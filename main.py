#!/usr/bin/env python
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:5046").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN", "")


# ----------------------------------------------------------------------
# Request helpers (add bearer token)
# ----------------------------------------------------------------------
def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _request(method: str, url: str, token: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers.update(_auth_headers(token))
    return requests.request(method, url, headers=headers, **kwargs)


# ----------------------------------------------------------------------
# API wrappers (unchanged)
# ----------------------------------------------------------------------
def upload_file(
    api_url: str, token: str, file_path: str, content_type: str
) -> Tuple[bool, str]:
    if not file_path:
        return False, "❌ No file selected."

    filename = os.path.basename(file_path)
    mime = f"application/{content_type}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime)}
            data = {"content_type": content_type}
            r = _request("POST", f"{api_url}/notes", token, files=files, data=data)
            r.raise_for_status()
            return True, r.json()["note_id"]
    except Exception as exc:
        return False, f"❌ {exc}"


def upload_text(api_url: str, token: str, name: str, content: str) -> Tuple[bool, str]:
    if not name or not content:
        return False, "❌ Both name and content are required."
    payload = {"name": name, "content": content}
    try:
        r = _request("POST", f"{api_url}/notes/text", token, json=payload)
        r.raise_for_status()
        return True, r.json()["note_id"]
    except Exception as exc:
        return False, f"❌ {exc}"


def list_notes(api_url: str, token: str) -> List[Tuple[str, str, str]]:
    r = _request("GET", f"{api_url}/notes", token)
    r.raise_for_status()
    return [(n["id"], n["name"], n["status"]) for n in r.json()]


def get_note_content(api_url: str, token: str, note_id: str) -> str:
    r = _request("GET", f"{api_url}/notes/{note_id}", token)
    r.raise_for_status()
    return r.json()["content"]


def process_note(api_url: str, token: str, note_id: str) -> Tuple[bool, str]:
    try:
        r = _request("POST", f"{api_url}/notes/{note_id}/process", token, timeout=120)
        r.raise_for_status()
        msg = r.json()
        return True, f"✅ Generated {msg['concepts_generated']} concepts."
    except Exception as exc:
        return False, f"❌ {exc}"


def list_concepts(api_url: str, token: str, note_id: str) -> List[Dict[str, Any]]:
    r = _request("GET", f"{api_url}/notes/{note_id}/concepts", token)
    r.raise_for_status()
    return r.json()


def create_quiz(
    api_url: str,
    token: str,
    note_ids: List[str],
    concept_limit: int,
    question_limit: int,
    mode: str,
) -> Tuple[bool, Dict[str, Any]]:
    payload = {
        "note_ids": note_ids,
        "concept_limit": concept_limit,
        "question_limit": question_limit,
        "mode": mode,
    }
    try:
        r = _request("POST", f"{api_url}/quizzes", token, json=payload)
        r.raise_for_status()
        return True, r.json()
    except Exception as exc:
        return False, f"❌ {exc}"


def submit_quiz(
    api_url: str, token: str, quiz_id: str, responses: List[str]
) -> Tuple[bool, Dict[str, Any]]:
    payload = {"responses": responses}
    try:
        r = _request("POST", f"{api_url}/quizzes/{quiz_id}/submit", token, json=payload)
        r.raise_for_status()
        return True, r.json()
    except Exception as exc:
        return False, f"❌ {exc}"


def delete_note(api_url: str, token: str, note_id: str) -> Tuple[bool, str]:
    try:
        r = _request("DELETE", f"{api_url}/notes/{note_id}", token)
        r.raise_for_status()
        return True, r.json()
    except Exception as exc:
        return False, f"❌ {exc}"


def list_quizzes(api_url: str, token: str) -> List[Dict[str, Any]]:
    r = _request("GET", f"{api_url}/quizzes", token)
    r.raise_for_status()
    return r.json()


def get_quiz_by_id(api_url: str, token: str, quiz_id: str) -> Dict[str, Any]:
    r = _request("GET", f"{api_url}/quizzes/{quiz_id}", token)
    r.raise_for_status()
    return r.json()


# ----------------------------------------------------------------------
# Small UI helper utilities
# ----------------------------------------------------------------------
def _format_note_choice(row: Tuple[str, str, str]) -> str:
    """Display label for a note dropdown: Name — ID"""
    nid, name, _status = row
    # Name first, then ID so display is readable but ID is easily extractable.
    return f"{name} — {nid}"


def _format_note_choices(rows: List[Tuple[str, str, str]]) -> List[str]:
    return [_format_note_choice(r) for r in rows]


def _format_quiz_choice(q: Dict[str, Any]) -> str:
    """Readable quiz label; embed the id at the end for extraction."""
    qid = q.get("id", "")
    qname = q.get("name") or f"Quiz {qid[:8]}"
    return f"{qname} — {qid}"


def _extract_id_from_display(sel: Optional[str]) -> Optional[str]:
    if not sel:
        return None
    if " — " in sel:
        return sel.split(" — ")[-1]
    return sel


def _extract_ids_from_display_list(sel_list: Optional[List[str]]) -> List[str]:
    if not sel_list:
        return []
    return [s.split(" — ")[-1] if " — " in s else s for s in sel_list]


# ----------------------------------------------------------------------
# UI – Gradio Blocks
# ----------------------------------------------------------------------
with gr.Blocks(title="ConceptCycle", theme=gr.themes.Ocean()) as client:
    # only store dynamic UI state here (last ids). API URL + token come from .env
    cfg_state = gr.State({"last_note_id": None, "last_quiz_id": None})

    gr.Markdown("# ConceptCycle")
    # gr.Markdown(
    #     f"**Loaded .env**  \nAPI base URL: `{API_URL}`  \nToken present: {'✅' if API_TOKEN else '❌ (not set)'}"
    # )

    # -----------------------
    # NOTES TAB
    # -----------------------
    with gr.Tab("🗂️ Notes"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Upload a file")
                file_input = gr.File(label="Choose a file", type="filepath")
                file_type_dd = gr.Dropdown(
                    ["txt", "pdf", "docx", "pptx", "png", "jpeg"],
                    label="File type (as expected by the server)",
                    value="txt",
                )
                upload_file_btn = gr.Button("Upload file", variant="primary")
                upload_file_status = gr.Textbox(label="Result", interactive=False)

            with gr.Column():
                gr.Markdown("### Upload raw text")
                txt_name = gr.Textbox(label="Note name")
                txt_content = gr.Textbox(label="Note content", lines=8)
                upload_txt_btn = gr.Button("Upload text", variant="primary")
                upload_txt_status = gr.Textbox(label="Result", interactive=False)

        with gr.Row():
            list_notes_btn = gr.Button("Refresh note list", variant="secondary")
            notes_df = gr.Dataframe(
                headers=["Name", "Status"],
                datatype=["str", "str"],
                interactive=False,
                label="Your notes",
                wrap=True,
            )
            selected_note = gr.Dropdown(
                label="Select a note",
                choices=[],
                interactive=True,
            )

        with gr.Row():
            with gr.Column():
                view_content_btn = gr.Button("Show raw content")
                note_content_box = gr.Textbox(
                    label="Note content", lines=10, interactive=False
                )
            with gr.Column():
                process_btn = gr.Button("Process → extract concepts", variant="primary")
                process_status = gr.Textbox(label="Processing", interactive=False)
            with gr.Column():
                delete_btn = gr.Button("❌ Delete selected note", variant="danger")
                delete_status = gr.Textbox(label="Delete result", interactive=False)

        # file upload callback (uses dotenv API_URL / API_TOKEN)
        def _upload_file(_cfg, fpath, ftype):
            ok, out = upload_file(API_URL, API_TOKEN, fpath, ftype)
            return out if ok else f"❌ {out}"

        upload_file_btn.click(
            _upload_file,
            inputs=[cfg_state, file_input, file_type_dd],
            outputs=upload_file_status,
        )

        # text upload
        def _upload_txt(_cfg, name, cont):
            ok, out = upload_text(API_URL, API_TOKEN, name, cont)
            return out if ok else f"❌ {out}"

        upload_txt_btn.click(
            _upload_txt,
            inputs=[cfg_state, txt_name, txt_content],
            outputs=upload_txt_status,
        )

        # Refresh notes (notes table + selected_note dropdown)
        def _refresh_notes(_cfg):
            notes = list_notes(API_URL, API_TOKEN)
            rows = [[n[1], n[2]] for n in notes]
            choices = _format_note_choices(notes)
            selected_val = choices[0] if choices else None
            return rows, gr.update(choices=choices, value=selected_val)

        list_notes_btn.click(
            _refresh_notes,
            inputs=cfg_state,
            outputs=[notes_df, selected_note],
        )

        # show raw content
        def _show_content(_cfg, sel_note_display):
            nid = _extract_id_from_display(sel_note_display)
            if not nid:
                return "⚠️ No note selected."
            try:
                return get_note_content(API_URL, API_TOKEN, nid)
            except Exception as exc:
                return f"❌ {exc}"

        view_content_btn.click(
            _show_content,
            inputs=[cfg_state, selected_note],
            outputs=note_content_box,
        )

        # process note
        def _process(cfg, sel_note_display):
            nid = _extract_id_from_display(sel_note_display)
            if not nid:
                return "⚠️ No note selected.", cfg
            ok, msg = process_note(API_URL, API_TOKEN, nid)
            new_cfg = cfg.copy()
            new_cfg["last_note_id"] = nid if ok else cfg.get("last_note_id")
            return msg, new_cfg

        process_btn.click(
            _process,
            inputs=[cfg_state, selected_note],
            outputs=[process_status, cfg_state],
        )

        # delete note (refreshes table + selected dropdown)
        def _delete_note(cfg, sel_note_display):
            nid = _extract_id_from_display(sel_note_display)
            if not nid:
                return "⚠️ No note selected.", [], gr.update(choices=[], value=None)
            ok, msg = delete_note(API_URL, API_TOKEN, nid)
            if not ok:
                return f"❌ {msg}", [], gr.update(choices=[], value=None)
            notes = list_notes(API_URL, API_TOKEN)
            rows = [[n[0], n[1], n[2]] for n in notes]
            choices = _format_note_choices(notes)
            upd_selected = gr.update(choices=choices, value=None)
            return "✅ Note deleted.", rows, upd_selected

        delete_btn.click(
            _delete_note,
            inputs=[cfg_state, selected_note],
            outputs=[delete_status, notes_df, selected_note],
        )

    # -----------------------
    # CONCEPTS TAB
    # -----------------------
    with gr.Tab("💡 Concepts"):
        concept_note_selector = gr.Dropdown(
            label="Select a note (to view its concepts)",
            choices=[],
            interactive=True,
        )
        refresh_concept_notes = gr.Button("Refresh notes")

        def _refresh_concept(_cfg):
            notes = list_notes(API_URL, API_TOKEN)
            choices = _format_note_choices(notes)
            return gr.update(choices=choices, value=choices[0] if choices else None)

        refresh_concept_notes.click(
            _refresh_concept,
            inputs=cfg_state,
            outputs=concept_note_selector,
        )

        concepts_df = gr.Dataframe(
            headers=[
                "Name",
                "Content",
                "Stability (days)",
                "Difficulty (percentage)",
                "Due",
                "Last review",
            ],
            datatype=["str"] * 10,
            interactive=False,
            label="Concepts for the selected note",
            wrap=True,
        )

        def _load_concepts(_cfg, sel_note_display):
            nid = _extract_id_from_display(sel_note_display)
            if not nid:
                return []
            raw = list_concepts(API_URL, API_TOKEN, nid)
            rows = []
            for c in raw:
                s = c.get("srs_info", {})
                rows.append(
                    [
                        c.get("name", ""),
                        c.get("content", ""),
                        "" if not (x := s.get("stability")) else round(float(x), 2),
                        (
                            ""
                            if not (x := s.get("difficulty"))
                            else round(((float(x) - 1) / 9) * 100, 2)
                        ),
                        (
                            ""
                            if not (x := s.get("due", ""))
                            else datetime.fromisoformat(x).strftime("%Y-%m-%d")
                        ),
                        (
                            ""
                            if not (x := s.get("last_review", ""))
                            else datetime.fromisoformat(x).strftime("%Y-%m-%d")
                        ),
                    ]
                )
            return rows

        concept_note_selector.change(
            _load_concepts,
            inputs=[cfg_state, concept_note_selector],
            outputs=concepts_df,
        )

    # -----------------------
    # QUIZZES TAB
    # -----------------------
    with gr.Tab("📝 Quizzes"):
        quiz_note_selector = gr.Dropdown(
            label="Choose notes for the quiz",
            choices=[],
            multiselect=True,
            interactive=True,
        )
        refresh_quiz_notes = gr.Button("Refresh notes")

        def _refresh_quiz_notes(_cfg):
            notes = list_notes(API_URL, API_TOKEN)
            choices = _format_note_choices(notes)
            return gr.update(choices=choices, value=None)

        refresh_quiz_notes.click(
            _refresh_quiz_notes,
            inputs=cfg_state,
            outputs=quiz_note_selector,
        )

        with gr.Row():
            concept_limit_n = gr.Slider(1, 20, value=5, step=1, label="Concept limit")
            question_limit_n = gr.Slider(
                1, 50, value=10, step=1, label="Question limit"
            )
            mode_dd = gr.Dropdown(
                ["due_only", "learning_only", "new_only", "mixed"],
                label="Mode",
                value="mixed",
                interactive=True,
            )
        create_quiz_btn = gr.Button("Create quiz", variant="primary")

        active_quiz_selector = gr.Dropdown(
            label="Select an active quiz to answer",
            choices=[],
            interactive=True,
        )
        refresh_active_quizzes_btn = gr.Button("Refresh active quizzes")

        def _refresh_active_quizzes(_cfg):
            quizzes = [
                q
                for q in list_quizzes(API_URL, API_TOKEN)
                if q.get("status") == "active"
            ]
            choices = [_format_quiz_choice(q) for q in quizzes]
            return gr.update(choices=choices, value=choices[0] if choices else None)

        refresh_active_quizzes_btn.click(
            _refresh_active_quizzes,
            inputs=cfg_state,
            outputs=active_quiz_selector,
        )

        active_quiz_df = gr.Dataframe(
            headers=["question", "answer"],
            datatype=["str", "str"],
            interactive=True,
            label="Answer the questions below (type in the “answer” column)",
        )
        submit_quiz_btn = gr.Button("Submit answers", variant="primary")
        submit_result_box = gr.JSON(label="Grading result")

        def _create_quiz(cfg, sel_note_displays, climit, qlimit, mode):
            note_ids = _extract_ids_from_display_list(sel_note_displays)
            if not note_ids:
                return {"error": "Select at least one note."}, gr.update(value=[])
            ok, out = create_quiz(API_URL, API_TOKEN, note_ids, climit, qlimit, mode)
            if not ok:
                return {"error": out}, gr.update(value=[])
            new_cfg = cfg.copy()
            new_cfg["last_quiz_id"] = out["id"]
            rows = [[q["question"], ""] for q in out.get("questions", [])]
            return out, gr.update(value=rows), new_cfg

        create_quiz_btn.click(
            _create_quiz,
            inputs=[
                cfg_state,
                quiz_note_selector,
                concept_limit_n,
                question_limit_n,
                mode_dd,
            ],
            outputs=[
                gr.JSON(label="Quiz metadata", visible=False),
                active_quiz_df,
                cfg_state,
            ],
        )

        def _load_active_quiz(cfg, sel_q_display):
            if not sel_q_display:
                return gr.update(value=[]), cfg
            qid = _extract_id_from_display(sel_q_display)
            data = get_quiz_by_id(API_URL, API_TOKEN, qid)
            new_cfg = cfg.copy()
            new_cfg["last_quiz_id"] = qid
            rows = []
            readonly = data.get("status") != "active"
            for q in data.get("questions", []):
                rows.append([q.get("question", ""), ""])
            df_update = gr.update(value=rows, interactive=not readonly)
            return df_update, new_cfg

        active_quiz_selector.change(
            _load_active_quiz,
            inputs=[cfg_state, active_quiz_selector],
            outputs=[active_quiz_df, cfg_state],
        )

        def _submit_quiz(cfg, df):
            quiz_id = cfg.get("last_quiz_id")
            if not quiz_id:
                return {"error": "No quiz loaded in this session."}
            answers = []
            try:
                if hasattr(df, "answer"):
                    answers = [str(r).strip() for r in df.answer]
                else:
                    answers = [str(row[1]).strip() for row in df] if df else []
            except Exception:
                answers = []
            if not answers or not all(map(bool, answers)):
                return {"error": "All questions must be attempted before submission"}
            ok, out = submit_quiz(API_URL, API_TOKEN, quiz_id, answers)
            if not ok:
                return {"error": out}
            return out

        submit_quiz_btn.click(
            _submit_quiz, inputs=[cfg_state, active_quiz_df], outputs=submit_result_box
        )

        completed_quiz_selector = gr.Dropdown(
            label="Select a completed quiz", choices=[], interactive=True
        )
        refresh_completed_quizzes_btn = gr.Button("Refresh completed quizzes")

        def _refresh_completed_quizzes(_cfg):
            quizzes = [
                q
                for q in list_quizzes(API_URL, API_TOKEN)
                if q.get("status") == "completed"
            ]
            choices = [_format_quiz_choice(q) for q in quizzes]
            return gr.update(choices=choices, value=choices[0] if choices else None)

        refresh_completed_quizzes_btn.click(
            _refresh_completed_quizzes,
            inputs=cfg_state,
            outputs=completed_quiz_selector,
        )

        completed_quiz_df = gr.Dataframe(
            headers=["question", "response", "grade", "feedback"],
            datatype=["str", "str", "int", "str"],
            interactive=False,
            label="Completed quiz info",
        )

        def _load_completed_quiz(_cfg, sel_q_display):
            if not sel_q_display:
                return gr.update(value=[])
            qid = _extract_id_from_display(sel_q_display)
            try:
                data = get_quiz_by_id(API_URL, API_TOKEN, qid)
            except Exception:
                return gr.update(value=[])
            rows = []
            for q in data.get("questions", []):
                rows.append(
                    [
                        q.get("question", ""),
                        q.get("response", ""),
                        q.get("grade", ""),
                        q.get("feedback", ""),
                    ]
                )
            return gr.update(value=rows)

        completed_quiz_selector.change(
            _load_completed_quiz,
            inputs=[cfg_state, completed_quiz_selector],
            outputs=[completed_quiz_df],
        )

    # # Footer
    # with gr.Row():
    #     gr.Markdown(
    #         """
    #         **Info:**
    #         • The UI reads API_URL and API_TOKEN from .env at startup.
    #         • API URL & token are not editable from the UI.
    #         • All requests go through the standard `requests` library.
    #         • Errors from the server appear verbatim in the output boxes.
    #         """
    #     )

if __name__ == "__main__":
    client.queue()
    client.launch(share=False, favicon_path="conceptcycle.jpg")
