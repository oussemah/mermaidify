# Image to Mermaid Diagram Server

This server provides an API to convert diagram images into Mermaid syntax text.
It uses a simulated iterative approach with placeholder models.

## API Endpoints

- `POST /image_to_diagram`
  - Accepts:
    - `image_path` (form data): Path to the image file (relative to the `uploads` directory).
    - `text_context` (form data, optional): Textual context for the image.
    - `synchronous` (form data, optional, 'true' or 'false'): If 'true', processes synchronously and returns the diagram. Defaults to 'false' for asynchronous processing.
  - Returns:
    - `session_id`
    - `diagram` (if synchronous and successful)
    - `status` (current status)

- `GET /status/<session_id>`
  - Accepts:
    - `session_id` (path parameter): The ID of the session.
  - Returns:
    - `session_id`
    - `status` ('unknown', 'in-progress', 'finished', 'error')
    - `diagram` (if status is 'finished')
    - `error_message` (if status is 'error')

## Setup

1.  **Clone the repository.**
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Mermaid to PNG Conversion (Future Real Implementation):**
    The current version simulates Mermaid to PNG conversion. For a real implementation,
    a tool like `mermaid-cli` (npm package: `@mermaid-js/mermaid-cli`) would be required.
    You would typically install it globally or as a project dependency:
    ```bash
    # Example: npm install -g @mermaid-js/mermaid-cli
    ```
    The `convert_mermaid_to_png` function in `app.py` would then need to be updated
    to use this tool (e.g., via `subprocess`).

5.  **Run the server:**
    ```bash
    python app.py
    ```
    The server will start on `http://0.0.0.0:5000`.

## Project Structure

- `app.py`: Main Flask application file.
- `requirements.txt`: Python package dependencies.
- `uploads/`: Directory for uploaded images and temporary files.
  - `uploads/mermaid_images/`: Directory for temporary PNGs generated from Mermaid syntax.
- `README.md`: This file.

## Testing

You can use tools like `curl` or Postman to interact with the API.

**Example (Asynchronous):**
1. Create a dummy file in the `uploads` directory (e.g., `touch uploads/example_diagram.png`).
2. Send request:
   ```bash
   curl -X POST -F "image_path=example_diagram.png" -F "text_context=A simple flow" http://localhost:5000/image_to_diagram
   ```
   (Replace `example_diagram.png` with your file)
3. Note the `session_id` from the response.
4. Check status:
   ```bash
   curl http://localhost:5000/status/<your_session_id>
   ```

**Example (Synchronous):**
```bash
curl -X POST -F "image_path=example_diagram.png" -F "synchronous=true" http://localhost:5000/image_to_diagram
```
