# Autonomous Code Review Agent System

An AI-powered code review system that automatically analyzes GitHub pull requests using autonomous agents. The system processes reviews asynchronously and provides structured feedback through a REST API.

## Features

- **Automated Code Analysis**: Leverages AI agents for insightful reviews.
- **Asynchronous Processing**: Efficiently handles long-running tasks using Celery.
- **RESTful API**: Provides endpoints for initiating and retrieving analysis results.
- **Multi-Language Support**: Analyzes code in various programming languages.
- **Comprehensive Feedback**:
  - Code style and formatting issues
  - Potential bugs and errors
  - Performance improvements
  - Best practices recommendations

## Architecture

The system is composed of several key components:

1. **FastAPI Application**: Manages HTTP requests and exposes REST endpoints.
2. **Celery Workers**: Handles code analysis tasks asynchronously.
3. **AI Agent**: Processes code analysis using advanced LLM models.
4. **Redis**: Stores task states and results.
5. **GitHub Integration**: Retrieves pull request details and code diffs.

## Prerequisites

- Python 3.8+
- Redis
- Git
- Celery

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/omkar-afk/autonomous-code-review-agent.git
   cd autonomous-code-review-agent
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

5. Configure environment variables in `.env`:

   ```plaintext
   GROQ_API_KEY=your_api_key
   GITHUB_TOKEN=your_github_token
   REDIS_URL=redis://localhost:6379
   ```

## Running the Application

1. Start Redis:

   ```bash
   redis-server
   ```

2. Start Celery workers:

   ```bash
   celery -A app.celery_config worker --loglevel=info
   ```

3. Start the FastAPI server:

   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`.

## API Documentation

### Endpoints

#### POST /analyze-pr
Initiates a new code review analysis.

**Request Body:**

```json
{
    "repo_url": "https://github.com/user/repo",
    "pr_number": 123,
    "github_token": "optional_token"
}
```

**Response:**

```json
{
    "task_id": "7f0edc15-0017-4f76-8c6a-ce99bb2a8e5d",
    "status": "pending"
}
```

#### GET /status/<task_id>
Check the status of an analysis task.

**Response:**

```json
{
    "task_id": "7f0edc15-0017-4f76-8c6a-ce99bb2a8e5d",
    "status": "pending"
}
```

If the results are ready you will get the output of the task as well.

#### GET /results/<task_id>
Retrieve the analysis results.

**Response:**

```json
{
    "task_id": "7f0edc15-0017-4f76-8c6a-ce99bb2a8e5d",
    "status": "completed",
    "result": {
        "files": [
            {
                "name": "file.py",
                "issues": [
                    {
                        "type": "style",
                        "line": 10,
                        "description": "Variable name is not descriptive",
                        "suggestion": "Rename variable to be more descriptive"
                    }
                ]
            }
        ],
        "summary": {
            "total_files": 6,
            "total_issues": 80,
            "critical_issues": 0,
            "total_files_analysed": 6,
            "analysis_start_time": "2025-01-05T17:51:10.730662",
            "analysis_end_time": "2025-01-05T17:51:39.620931",
            "failed_files": 0,
            "status": "success",
            "error": null
        }
    }
}
```

## Design Decisions

1. **Asynchronous Processing**: Utilized Celery to enable efficient handling of long-running code analysis tasks, ensuring scalability and responsiveness.

2. **AI Agent Framework**: Implemented using LangGraph for:
   - Flexible agent architecture
   - Built-in support for complex reasoning
   - Easy integration with LLM APIs

3. **Storage Solution**: Selected Redis for:
   - Fast access to task states and results
   - High scalability and reliability

4. **LLM Model**: Adopted GROQ LLaMA 8B 8192 for its:
   - High throughput
   - Extensive token context window
   - Optimized reasoning capabilities

5. **RESTful API**: Designed intuitive and consistent endpoints to simplify client integration.

## Future Enhancements

- Support for additional LLM providers
- Advanced security features, including token-based authentication
- Scalability improvements with distributed task queues
