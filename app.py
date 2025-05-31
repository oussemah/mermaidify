import uuid
import threading
import os
import time
from flask import Flask, request, jsonify
import subprocess # For calling mmdc
import requests

# Initialize Flask app
app = Flask(__name__)

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

MAX_ITERATIONS = 5
MODEL_API_ENDPOINT_INITIAL = "http://localhost:12345/qwen25vl7b/initial_diagram"
MODEL_API_ENDPOINT_COMPARISON = "http://localhost:12345/qwen25vl7b/compare_diagram"

def call_vision_model_for_initial_diagram(image_path, text_context):
    """
    Placeholder for QWEN2.5-VL-7B model: initial diagram generation.
    """
    app.logger.info(f"QWEN_MODEL_CALL: Initial diagram for {image_path} with context: '{text_context}'")
    payload = {
        "image_path": image_path,
        "text_context": text_context,
        "prompt": "Describe this image and generate a Mermaid syntax diagram based on it."
    }
    try:
        # response = requests.post(MODEL_API_ENDPOINT_INITIAL, json=payload, timeout=60)
        # response.raise_for_status()
        # model_output = response.json()
        # current_mermaid_diagram = model_output.get("mermaid_diagram", "")
        app.logger.warning(f"QWEN_MODEL_CALL: Dummy endpoint {MODEL_API_ENDPOINT_INITIAL} not reachable. Using simulation.")
        time.sleep(1) # Reduced sleep time for faster testing
        current_mermaid_diagram = f"graph TD; A[Image: {os.path.basename(image_path)}] --> B(Initial QWEN Description);"
        if text_context:
            current_mermaid_diagram += f" B --> C{{Context: {text_context}}};"
        if not current_mermaid_diagram:
            raise ValueError("Model returned an empty diagram.")
        app.logger.info(f"QWEN_MODEL_CALL: Successfully received initial diagram (simulated).")
        return current_mermaid_diagram
    except requests.exceptions.RequestException as e:
        app.logger.error(f"QWEN_MODEL_CALL: API request failed for initial diagram: {e}")
        time.sleep(1)
        fallback_diagram = f"graph TD; A[Image: {os.path.basename(image_path)}] --> B(Fallback Initial Description);"
        if text_context:
            fallback_diagram += f" B --> C{{Context: {text_context}}};"
        app.logger.warning(f"QWEN_MODEL_CALL: Using fallback diagram due to API error.")
        return fallback_diagram
    except (ValueError, KeyError) as e:
        app.logger.error(f"QWEN_MODEL_CALL: Error processing model response for initial diagram: {e}")
        time.sleep(1)
        fallback_diagram = f"graph TD; A[Image: {os.path.basename(image_path)}] --> B(Fallback Error Description);"
        app.logger.warning(f"QWEN_MODEL_CALL: Using fallback diagram due to processing error.")
        return fallback_diagram

def call_vision_model_for_comparison(original_image_path, generated_png_path, current_mermaid_diagram, iteration):
    """
    Placeholder for QWEN2.5-VL-7B model: comparison and refinement.
    """
    app.logger.info(f"QWEN_MODEL_CALL: Comparing {original_image_path} with {generated_png_path} (Iteration {iteration})")
    payload = {
        "original_image_path": original_image_path,
        "generated_image_path": generated_png_path,
        "current_mermaid_diagram": current_mermaid_diagram,
        "prompt": ("Compare the generated image (from the provided Mermaid diagram) with the original image. "
                   "Point out differences and provide an updated Mermaid diagram to make the generated image "
                   "more similar to the original. If they are very similar, indicate it's final.")
    }
    try:
        # response = requests.post(MODEL_API_ENDPOINT_COMPARISON, json=payload, timeout=120)
        # response.raise_for_status()
        # model_output = response.json()
        # updated_diagram = model_output.get("updated_mermaid_diagram", current_mermaid_diagram)
        # is_final = model_output.get("is_final", False)
        # feedback = model_output.get("feedback", "No feedback from model.")
        app.logger.warning(f"QWEN_MODEL_CALL: Dummy endpoint {MODEL_API_ENDPOINT_COMPARISON} not reachable. Using simulation.")
        time.sleep(1) # Reduced sleep time
        feedback = f"QWEN Feedback for iteration {iteration} (simulated)."
        updated_diagram = current_mermaid_diagram + f" Iteration{iteration}_QWEN --> Node{iteration}_QWEN;"
        if iteration >= MAX_ITERATIONS - 1: # iteration is 0-indexed
            is_final = True
            feedback = "Diagram is now considered final by the QWEN model (simulated)."
        else:
            is_final = False
        app.logger.info(f"QWEN_MODEL_CALL: Successfully received comparison result (simulated). Final: {is_final}")
        return {'is_final': is_final, 'updated_mermaid_diagram': updated_diagram, 'feedback': feedback}
    except requests.exceptions.RequestException as e:
        app.logger.error(f"QWEN_MODEL_CALL: API request failed for comparison: {e}")
        time.sleep(1)
        feedback = f"Fallback QWEN Feedback for iteration {iteration} due to API error."
        updated_diagram = current_mermaid_diagram + f" Iteration{iteration}_Fallback --> Node{iteration}_Fallback;"
        is_final = iteration >= MAX_ITERATIONS -1
        app.logger.warning(f"QWEN_MODEL_CALL: Using fallback comparison due to API error. Final: {is_final}")
        return {'is_final': is_final, 'updated_mermaid_diagram': updated_diagram, 'feedback': feedback}
    except (ValueError, KeyError) as e:
        app.logger.error(f"QWEN_MODEL_CALL: Error processing model response for comparison: {e}")
        time.sleep(1)
        feedback = f"Fallback QWEN Feedback for iteration {iteration} due to processing error."
        updated_diagram = current_mermaid_diagram + f" Iteration{iteration}_ProcErr --> Node{iteration}_ProcErr;"
        is_final = iteration >= MAX_ITERATIONS -1
        app.logger.warning(f"QWEN_MODEL_CALL: Using fallback comparison due to processing error. Final: {is_final}")
        return {'is_final': is_final, 'updated_mermaid_diagram': updated_diagram, 'feedback': feedback}

def convert_mermaid_to_png(mermaid_text, session_id, iteration):
    """
    Converts Mermaid text to a PNG image using mmdc (mermaid-cli).
    Returns a path to the generated PNG.
    If conversion fails, it returns path to a dummy PNG with error info.
    """
    app.logger.info(f"MERMAID_CONVERSION: Starting for session {session_id}, Iteration {iteration}")

    base_filename = f"session_{session_id}_iter_{iteration}"
    # Ensure temp_mermaid_file_path is unique if multiple threads/processes could write simultaneously
    # For threading, session_id and iteration should be sufficient.
    temp_mermaid_file_path = os.path.join(app.config['GENERATED_MERMAID_IMAGES_FOLDER'], f"{base_filename}.mmd")
    generated_png_path = os.path.join(app.config['GENERATED_MERMAID_IMAGES_FOLDER'], f"{base_filename}.png")

    try:
        with open(temp_mermaid_file_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_text)
        app.logger.debug(f"MERMAID_CONVERSION: Temporary Mermaid file created at {temp_mermaid_file_path}")

        mmdc_command = ['mmdc', '-i', temp_mermaid_file_path, '-o', generated_png_path, '-w', '1024', '-H', '768']
        app.logger.debug(f"MERMAID_CONVERSION: Executing command: {' '.join(mmdc_command)}")

        result = subprocess.run(mmdc_command, capture_output=True, text=True, timeout=30, check=False)

        if result.returncode != 0:
            error_message = (f"Mermaid to PNG conversion failed. Exit code: {result.returncode}.\n"
                             f"Stderr: {result.stderr.strip()}\nStdout: {result.stdout.strip()}")
            app.logger.error(f"MERMAID_CONVERSION: {error_message}")
            with open(generated_png_path, 'w', encoding='utf-8') as f_err: # Create dummy error PNG
                f_err.write(f"Error during mmdc conversion:\n{result.stderr.strip()}")
            # Not raising an exception here to allow the model to "see" the broken image.
            # A stricter error handling might raise an exception.
            return generated_png_path

        app.logger.info(f"MERMAID_CONVERSION: PNG image successfully created at {generated_png_path}")
        return generated_png_path

    except FileNotFoundError:
        msg = "`mmdc` command not found. Ensure @mermaid-js/mermaid-cli is installed globally and in PATH."
        app.logger.error(f"MERMAID_CONVERSION: {msg}")
        with open(generated_png_path, 'w', encoding='utf-8') as f_err:
            f_err.write(msg)
        return generated_png_path # Return path to dummy error PNG

    except subprocess.TimeoutExpired:
        msg = "`mmdc` command timed out after 30 seconds."
        app.logger.error(f"MERMAID_CONVERSION: {msg}")
        with open(generated_png_path, 'w', encoding='utf-8') as f_err:
            f_err.write(msg)
        return generated_png_path # Return path to dummy error PNG

    except Exception as e:
        msg = f"An unexpected error occurred during Mermaid to PNG conversion: {str(e)}"
        app.logger.error(msg, exc_info=True)
        with open(generated_png_path, 'w', encoding='utf-8') as f_err:
            f_err.write(msg)
        return generated_png_path # Return path to dummy error PNG
    finally:
        if os.path.exists(temp_mermaid_file_path):
            try:
                os.remove(temp_mermaid_file_path)
                app.logger.debug(f"MERMAID_CONVERSION: Cleaned up temporary file {temp_mermaid_file_path}")
            except Exception as e_clean:
                app.logger.error(f"MERMAID_CONVERSION: Error cleaning temporary file {temp_mermaid_file_path}: {e_clean}")

def process_image_to_diagram(session_id):
    app.logger.info(f"PROCESS_DIAGRAM: Starting for session {session_id}")
    with sessions_lock:
        session_data = sessions.get(session_id)
        if not session_data:
            app.logger.error(f"PROCESS_DIAGRAM: Session {session_id} not found.")
            return
        image_path = session_data['image_path']
        text_context = session_data['text_context']

    generated_png_path = None # Initialize path for generated PNG

    try:
        current_mermaid_diagram = call_vision_model_for_initial_diagram(image_path, text_context)
        app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Initial diagram: '{current_mermaid_diagram[:100]}...'")

        for i in range(MAX_ITERATIONS):
            app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Iteration {i+1}/{MAX_ITERATIONS}")

            # Clean up PNG from the previous iteration, if it exists
            if generated_png_path and os.path.exists(generated_png_path):
                try:
                    os.remove(generated_png_path)
                    app.logger.debug(f"PROCESS_DIAGRAM: Cleaned up old PNG: {generated_png_path}")
                except Exception as e_clean:
                    app.logger.error(f"PROCESS_DIAGRAM: Error cleaning old PNG {generated_png_path}: {e_clean}")

            generated_png_path = convert_mermaid_to_png(current_mermaid_diagram, session_id, i)
            app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - New PNG path: {generated_png_path}")


            comparison_result = call_vision_model_for_comparison(image_path, generated_png_path, current_mermaid_diagram, i)
            current_mermaid_diagram = comparison_result['updated_mermaid_diagram']
            app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Updated diagram: '{current_mermaid_diagram[:100]}...'")

            if comparison_result['is_final']:
                app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Model indicated diagram is final.")
                break

        # Update session with final diagram
        with sessions_lock:
            sessions[session_id]['diagram'] = current_mermaid_diagram
            sessions[session_id]['status'] = 'finished'
        app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Finished successfully.")

    except Exception as e:
        app.logger.error(f"PROCESS_DIAGRAM: Session {session_id} - Error during processing: {e}", exc_info=True)
        with sessions_lock:
            sessions[session_id]['status'] = 'error'
            sessions[session_id]['error_message'] = str(e)
    finally:
        # Final cleanup of the last generated PNG file, if it exists
        if generated_png_path and os.path.exists(generated_png_path):
            try:
                os.remove(generated_png_path)
                app.logger.info(f"PROCESS_DIAGRAM: Session {session_id} - Cleaned up final PNG in `finally` block: {generated_png_path}")
            except Exception as cleanup_e:
                app.logger.error(f"PROCESS_DIAGRAM: Session {session_id} - Error cleaning final PNG in `finally` block: {cleanup_e}")

def generate_diagram_sync(session_id):
    app.logger.info(f"Starting synchronous generation for session: {session_id}")
    process_image_to_diagram(session_id)
    with sessions_lock: # Ensure thread-safe access
        session = sessions[session_id]
        diagram = session.get('diagram')
        if session['status'] == 'error':
            raise Exception(session.get('error_message', 'Unknown error during synchronous generation'))
    app.logger.info(f"Finished synchronous generation for session: {session_id}")
    return diagram

def generate_diagram_async(session_id):
    app.logger.info(f"Starting asynchronous generation for session: {session_id}")
    process_image_to_diagram(session_id) # This handles its own errors by updating the session
    app.logger.info(f"Finished asynchronous generation for session: {session_id}")

@app.route('/image_to_diagram', methods=['POST'])
def image_to_diagram():
    app.logger.info("Received request for /image_to_diagram")
    if 'image_path' not in request.form:
        app.logger.warning("Request missing 'image_path' in form data.")
        return jsonify({"error": "Missing 'image_path' in form data"}), 400

    image_path_relative = request.form['image_path']
    # Basic security: prevent directory traversal.
    # Normalize path and ensure it's within UPLOAD_FOLDER.
    safe_image_path_relative = os.path.normpath(os.path.join('/', image_path_relative)).lstrip('/')
    image_path_full = os.path.join(app.config['UPLOAD_FOLDER'], safe_image_path_relative)

    if not os.path.abspath(image_path_full).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
        app.logger.error(f"Potential directory traversal attempt: {image_path_relative}")
        return jsonify({"error": "Invalid image path."}), 400

    if not os.path.exists(image_path_full):
        # For testing, create a dummy file if it doesn't exist.
        # In production, this should be an error or handled by file upload logic.
        try:
            os.makedirs(os.path.dirname(image_path_full), exist_ok=True) # Ensure directory exists
            with open(image_path_full, 'a'): pass # Create empty file
            app.logger.info(f"Created dummy file for testing: {image_path_full}")
        except Exception as e_create:
            app.logger.error(f"Could not create dummy file {image_path_full}: {e_create}")
            return jsonify({"error": f"Image not found and dummy creation failed: {image_path_relative}"}), 404

    text_context = request.form.get('text_context', None)
    synchronous_str = request.form.get('synchronous', 'false').lower()
    synchronous = synchronous_str == 'true'
    session_id = str(uuid.uuid4())

    with sessions_lock:
        sessions[session_id] = {
            'status': 'in-progress',
            'image_path': image_path_full,
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
            app.logger.error(f"Exception during synchronous processing for {session_id}: {e}", exc_info=True)
            # Error status should already be set in the session by process_image_to_diagram
            error_message = str(e)
            with sessions_lock: # Ensure we get the latest error message if any
                if session_id in sessions and sessions[session_id]['status'] == 'error' and sessions[session_id]['error_message']:
                    error_message = sessions[session_id]['error_message']
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
        # Retrieve a copy if session data is mutable and modified outside lock,
        # but here session[key] assignments are atomic or within lock.
        # So direct access or .get() is fine.
        session = sessions.get(session_id)

    if not session:
        app.logger.warning(f"Session not found: {session_id}")
        return jsonify({"session_id": session_id, "status": "unknown"}), 404

    # Construct response based on the retrieved session data
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
    app.run(debug=True, host='0.0.0.0', port=5000)
