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
4.  **Install and Configure Ollama (Required for AI Model Interaction):**
    This application uses the QWEN multimodal model (`qwen2.5vl:7b-q8_0`) served via Ollama.
    *   **Install Ollama:** Follow the official instructions at [https://ollama.com/download](https://ollama.com/download) for your operating system (Ubuntu is the target server system).
    *   **Pull the QWEN model:** After installing Ollama, run the following command in your terminal:
        ```bash
        ollama pull qwen2.5vl:7b-q8_0
        ```
    *   **Ensure Ollama is running:** The Ollama server typically runs automatically after installation. The application expects it to be available at `http://localhost:11434`. You can check its status or start it as per the Ollama documentation.

5.  **Install Node.js and Mermaid CLI for Mermaid to PNG Conversion (Required):**
    The application uses `@mermaid-js/mermaid-cli` (command: `mmdc`) to convert Mermaid text to PNG images. You need to install Node.js and npm first, then install `mermaid-cli`.

    **On Ubuntu:**
    ```bash
    # Install Node.js (e.g., LTS version, adjust as needed)
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs

    # Verify Node.js and npm installation
    node -v
    npm -v

    # Install mermaid-cli globally
    sudo npm install -g @mermaid-js/mermaid-cli

    # Verify mmdc installation
    mmdc --version
    ```
    The `convert_mermaid_to_png` function in `app.py` uses `mmdc` via `subprocess`. Ensure it's in your system's PATH.

6.  **Run the server:**
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
