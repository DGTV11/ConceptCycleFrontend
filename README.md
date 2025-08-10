# ConceptCycle Gradio frontend

## Basic deployment

1. Clone repo
```bash
git clone git@github.com:DGTV11/ConceptCycleGradioFrontend.git
```

OR 

```bash
git clone https://github.com/DGTV11/ConceptCycleGradioFrontend.git
```

<!-- 2. Install dependencies -->
<!-- ```bash -->
<!-- pip install uv -->
<!-- uv sync -->
<!-- ``` -->
2. Install Docker and Docher Compose

3. Add `.env` file to directory and configure
```env
LLM_API_BASE_URL=<fill me>
LLM_API_KEY=<fill me>
LLM_NAME=<fill me>
VLM_API_BASE_URL=<fill me>
VLM_API_KEY=<fill me>
VLM_NAME=<fill me>
CHUNK_MAX_TOKENS=<fill me>
DEBUG_MODE=<fill me>
```

3. Ensure `.env` and `db.sqlite` files exist
```sh
touch .env db.sqlite
```

4. Run server
<!-- ```bash -->
<!-- uv run fastapi dev --port=5046 -->
<!-- ``` -->
<!---->
<!-- OR -->
<!---->
<!-- ```bash -->
<!-- uv run fastapi run --port=5046 -->
<!-- ``` -->
```bash
docker compose up
```

OR

```bash
docker compose up -d
```

## Notes

- I recommend testing endpoints using ![httpie](https://httpie.io/) for sanity reasons
- You should use this API with conjunction with a suitable frontend
- API recommended usage:
    1) `POST /notes` or `POST /notes/text` (make notes) 
    2) `POST /notes/{note_id}/process` (process notes into concepts) 
    3) Go back to step 1 to add more notes and repeat as needed
    4) `POST /quizzes` (start quiz based on concepts attached to input notes) 
    5) `POST /quizzes/{quiz_id}/submit` (submit quiz)
    6) Go back to step 4 to make new quiz or go back to step 1 to add more notes and repeat as needed
