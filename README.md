# ConceptCycle Gradio frontend

![ConceptCycle logo](conceptcycle.jpg)

See backend code at [ConceptCycleBackend](https://github.com/DGTV11/ConceptCycleBackend)

## Basic deployment

1. Clone repo
```bash
git clone git@github.com:DGTV11/ConceptCycleFrontend.git
```

OR 

```bash
git clone https://github.com/DGTV11/ConceptCycleFrontend.git
```

<!-- 2. Install dependencies -->
<!-- ```bash -->
<!-- pip install uv -->
<!-- uv sync -->
<!-- ``` -->
2. Install Docker and Docher Compose

3. Add `.env` file to directory and configure
```env
API_URL=<fill me>
API_TOKEN=<fill me>
```

3. Ensure `.env` file exists
```sh
touch .env
```

4. Run server
```bash
docker compose up
```

OR

```bash
docker compose up -d
```
