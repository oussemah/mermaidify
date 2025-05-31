import uuid
import threading
import os
import time
from flask import Flask, request, jsonify
import shutil # For cleaning up simulated generated PNGs

# Initialize Flask app
app = Flask(__name__)

# In-memory storage for session data
sessions = {}
sessions_lock = threading.Lock()

UPLOAD_FOLDER = 'uploads'
GENERATED_MERMAID_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'mermaid_images')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(GENERATED_MERMAID_IMAGES_FOLDER):
    os.makedirs(GENERATED_MERMAID_IMAGES_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_MERMAID_IMAGES_FOLDER'] = GENERATED_MERMAID_IMAGES_FOLDER

# --- Core Diagram Generation Logic & Model Placeholders ---

MAX_ITERATIONS = 5 # Max refinement loops

def call_vision_model_for_initial_diagram(image_path, text_context):
    """Placeholder for vision model: initial diagram generation."""
    app.logger.info(f"MODEL_CALL: Initial diagram for {image_path} with context: '{text_context}'")
    time.sleep(2) # Simulate model processing time
    # Simulate a basic diagram based on image path and context
    diagram = f"graph TD; A[Image: {os.path.basename(image_path)}] --> B(Initial Description);"
    if text_context:
        diagram += f" B --> C{{Context: {text_context}}};"
    return diagram

def convert_mermaid_to_png(mermaid_text, session_id, iteration):
    """
    Placeholder for Mermaid to PNG conversion.
    In a real app, this would use a tool like mermaid-cli.
    (e.g., using: npm install -g @mermaid-js/mermaid-cli)
    Returns a path to the generated PNG.
    """
    app.logger.info(f"MERMAID_CONVERSION: Session {session_id}, Iteration {iteration}")
    time.sleep(1) # Simulate conversion time
    # Simulate a generated PNG file
    # Path needs to be unique enough for concurrent sessions/iterations
    generated_png_filename = f"session_{session_id}_iter_{iteration}.png"
    generated_png_path = os.path.join(app.config['GENERATED_MERMAID_IMAGES_FOLDER'], generated_png_filename)

    # Create a dummy PNG file for simulation purposes
    with open(generated_png_path, 'w') as f:
        f.write(f"Simulated PNG content for: {mermaid_text}")
    app.logger.info(f"MERMAID_CONVERSION: Simulated PNG created at {generated_png_path}")
    return generated_png_path

def call_vision_model_for_comparison(original_image_path, generated_png_path, current_mermaid_diagram, iteration):
    """
    Placeholder for vision model: comparison and refinement.
    Returns a dict: {'is_final': bool, 'updated_mermaid_diagram': str, 'feedback': str}
    """
    app.logger.info(f"MODEL_CALL: Comparing {original_image_path} with {generated_png_path} (Iteration {iteration})")
    time.sleep(2) # Simulate model processing time

    feedback = f"Feedback for iteration {iteration}."
    # Simulate refinement: add a new node in each iteration
    updated_mermaid_diagram = current_mermaid_diagram + f" Iteration{iteration} --> Node{iteration};"

    # Simulate reaching the "final" state after a few iterations
    if iteration >= MAX_ITERATIONS -1 : # -1 because iteration is 0-indexed in the loop
        is_final = True
        feedback = "Diagram is now considered final by the model."
        app.logger.info(f"MODEL_CALL: Diagram for {original_image_path} is final after iteration {iteration}.")
    else:
        is_final = False
        app.logger.info(f"MODEL_CALL: Diagram for {original_image_path} needs further refinement (Iteration {iteration}).")

    return {'is_final': is_final, 'updated_mermaid_diagram': updated_mermaid_diagram, 'feedback': feedback}

def process_image_to_diagram(session_id):
    """Main logic for processing an image and generating a Mermaid diagram."""
    app.logger.info(f"PROCESS_DIAGRAM: Starting for session {session_id}")

    with sessions_lock:
        session_data = sessions.get(session_id)
        if not session_data:
            app.logger.error(f"PROCESS_DIAGRAM: Session {session_id} not found.")
            return
        image_path = session_data['image_path']
        text_context = session_data['text_context']

    generated_png_path = None # To keep track for cleanup
    try:
        # 1. Initial diagram generation
        current_mermaid_diagram = call_vision_model_for_initial_diagram(image_path, text_context)
        app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Initial diagram: {current_mermaid_diagram}")

        for i in range(MAX_ITERATIONS):
            app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Iteration {i+1}/{MAX_ITERATIONS}")

            # 2. Convert current Mermaid diagram to PNG
            if generated_png_path and os.path.exists(generated_png_path): # Clean up previous iteration's PNG
                os.remove(generated_png_path)

            generated_png_path = convert_mermaid_to_png(current_mermaid_diagram, session_id, i)

            # 3. Compare with original image and refine
            comparison_result = call_vision_model_for_comparison(image_path, generated_png_path, current_mermaid_diagram, i)

            current_mermaid_diagram = comparison_result['updated_mermaid_diagram']
            app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Updated diagram: {current_mermaid_diagram}")

            if comparison_result['is_final']:
                app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Model indicated diagram is final.")
                break

        # Final cleanup of the last generated PNG
        if generated_png_path and os.path.exists(generated_png_path):
            os.remove(generated_png_path)
            app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Cleaned up final PNG: {generated_png_path}")

        # 4. Update session with final diagram
        with sessions_lock:
            sessions[session_id]['diagram'] = current_mermaid_diagram
            sessions[session_id]['status'] = 'finished'
        app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Finished successfully.")

    except Exception as e:
        app.logger.error(f"PROCESS_DIAGRAM: Session {session_id} - Error during processing: {e}", exc_info=True)
        with sessions_lock:
            sessions[session_id]['status'] = 'error'
            sessions[session_id]['error_message'] = str(e)
        # Clean up any lingering PNG if an error occurred
        if generated_png_path and os.path.exists(generated_png_path):
            try:
                os.remove(generated_png_path)
                app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Cleaned up PNG after error: {generated_png_path}")
            except Exception as cleanup_e:
                app.logger.error(f"PROCESS_DIAGRAM: Session {session_id} - Error cleaning up PNG: {cleanup_e}")


# --- Updated Synchronous and Asynchronous Wrappers ---
def generate_diagram_sync(session_id):
    """Synchronous diagram generation using the core processing logic."""
    app.logger.info(f"Starting synchronous generation for session: {session_id}")
    process_image_to_diagram(session_id) # Call the main logic
    with sessions_lock: # Retrieve the result
        # Check if session exists and has status before trying to access diagram/error
        session = sessions.get(session_id)
        if not session:
            # This case should ideally not be reached if process_image_to_diagram was called
            app.logger.error(f"Session {session_id} not found after sync processing.")
            raise Exception(f"Session {session_id} disappeared during processing.")

        diagram = session.get('diagram')
        if session['status'] == 'error':
            raise Exception(session['error_message'])
    app.logger.info(f"Finished synchronous generation for session: {session_id}")
    return diagram

def generate_diagram_async(session_id):
    """Asynchronous diagram generation using the core processing logic."""
    app.logger.info(f"Starting asynchronous generation for session: {session_id}")
    process_image_to_diagram(session_id) # Call the main logic
    app.logger.info(f"Finished asynchronous generation for session: {session_id}")


# --- Flask Routes ---
@app.route('/image_to_diagram', methods=['POST'])
def image_to_diagram():
    app.logger.info("Received request for /image_to_diagram")
    if 'image_path' not in request.form:
        app.logger.warning("Request missing 'image_path' in form data.")
        return jsonify({"error": "Missing 'image_path' in form data"}), 400

    image_path_relative = request.form['image_path']
    # IMPORTANT: This assumes image_path_relative is a path *within* UPLOAD_FOLDER.
    # For security, ensure it doesn't allow directory traversal (e.g., '../').
    # For now, we'll just join it. A real app needs robust path validation.
    image_path_full = os.path.join(app.config['UPLOAD_FOLDER'], image_path_relative)

    # Basic validation: check if the (mock) file exists.
    # In a real scenario, if it's a file upload, the file would be saved first.
    if not os.path.exists(image_path_full):
        # To make this testable without actual file uploads yet, create a dummy file if it doesn't exist
        # This is for ease of testing the flow. In a real app, image_path must exist or be uploaded.
        try:
            # Ensure the UPLOAD_FOLDER itself exists before trying to create a file in it
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
                app.logger.info(f"Created UPLOAD_FOLDER at {app.config['UPLOAD_FOLDER']}")
            open(image_path_full, 'a').close() # Create an empty file
            app.logger.info(f"Created dummy file for testing: {image_path_full}")
        except Exception as e:
            app.logger.error(f"Could not create dummy file {image_path_full}: {e}")
            return jsonify({"error": f"Image not found at specified path: {image_path_relative} and dummy creation failed."}), 404


    text_context = request.form.get('text_context', None)
    synchronous_str = request.form.get('synchronous', 'false').lower()
    synchronous = synchronous_str == 'true'
    session_id = str(uuid.uuid4())

    with sessions_lock:
        sessions[session_id] = {
            'status': 'in-progress',
            'image_path': image_path_full, # Store full path for processing
            'text_context': text_context,
            'diagram': None,
            'error_message': None
        }
    app.logger.info(f"Created session: {session_id} for image: {image_path_relative}, sync: {synchronous}")

    if synchronous:
        app.logger.debug(f"Processing session {session_id} synchronously.")
        try:
            diagram_text = generate_diagram_sync(session_id)
            return jsonify({"session_id": session_id, "diagram": diagram_text, "status": "finished"}), 200
        except Exception as e:
            app.logger.error(f"Exception during synchronous processing for {session_id}: {e}")
            # The error status is already set by process_image_to_diagram or generate_diagram_sync
            with sessions_lock: # Ensure we have the latest error message if generate_diagram_sync failed early
                error_message = sessions.get(session_id, {}).get('error_message', str(e))
            return jsonify({"session_id": session_id, "error": error_message, "status": "error"}), 500
    else:
        app.logger.debug(f"Starting background thread for session {session_id}.")
        thread = threading.Thread(target=generate_diagram_async, args=(session_id,))
        thread.start()
        return jsonify({"session_id": session_id, "status": "in-progress"}), 202


@app.route('/status/<session_id>', methods=['GET'])
def get_status(session_id):
    app.logger.info(f"Received status request for session: {session_id}")
    with sessions_lock:
        session = sessions.get(session_id)

    if not session:
        app.logger.warning(f"Session not found: {session_id}")
        return jsonify({"session_id": session_id, "status": "unknown"}), 404

    response = {
        "session_id": session_id,
        "status": session['status']
    }
    if session['status'] == 'finished':
        response['diagram'] = session.get('diagram')
    elif session['status'] == 'error':
        response['error_message'] = session.get('error_message')

    app.logger.debug(f"Returning status for session {session_id}: {response}")
    return jsonify(response), 200

if __name__ == '__main__':
    # Note: shutil import is present, but os.remove is used for simplicity for now.
    # If more complex file/directory operations were needed, shutil would be handy.
    app.run(debug=True, host='0.0.0.0', port=5000)
