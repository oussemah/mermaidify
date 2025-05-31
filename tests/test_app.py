import pytest
import os
import json
import subprocess # For CompletedProcess and TimeoutExpired
from unittest.mock import MagicMock, patch, mock_open as unittest_mock_open

# Assuming app.py is in the parent directory or PYTHONPATH is set up
from app import app as flask_app

@pytest.fixture
def app_instance(): # Renamed from 'app' to avoid conflict with flask_app import
    """Create and configure a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
        # Ensure UPLOAD_FOLDER and GENERATED_MERMAID_IMAGES_FOLDER are set and exist for tests
        # This might involve creating temp dirs for tests in a more complex setup
    })
    # Create the necessary folders if they don't exist, to prevent errors during tests
    # In a real test suite, you might use pytest's tmp_path fixture for this
    os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(flask_app.config['GENERATED_MERMAID_IMAGES_FOLDER'], exist_ok=True)

    yield flask_app

@pytest.fixture
def client(app_instance): # Depends on the renamed fixture
    """A test client for the app."""
    return app_instance.test_client()

def test_image_to_diagram_missing_image_path(client):
    """Test /image_to_diagram when image_path is missing."""
    response = client.post('/image_to_diagram', data={})
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'error' in json_data
    assert json_data['error'] == "Missing 'image_path' in form data"

def test_image_to_diagram_image_not_found_and_no_dummy_creation(client, mocker):
    """Test /image_to_diagram when the image file does not exist and dummy creation is mocked to fail."""
    mocker.patch('os.path.exists', return_value=False)
    # Mock os.makedirs and open to simulate failure in creating dummy file
    # We target 'builtins.open' as 'open' is a built-in function.
    mocker.patch('builtins.open', side_effect=OSError("Failed to create file"))


    response = client.post('/image_to_diagram', data={'image_path': 'non_existent_image.png'})

    assert response.status_code == 404
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'Image not found and dummy creation failed' in json_data['error']


def test_status_unknown_session(client):
    """Test /status for a session_id that doesn't exist."""
    response = client.get('/status/non_existent_session_id')
    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data['status'] == 'unknown'
    assert json_data['session_id'] == 'non_existent_session_id'

def test_image_to_diagram_path_traversal_attempt(client):
    """Test /image_to_diagram with a path traversal attempt."""
    traversal_paths = [
        "../etc/passwd",
        "..\\..\\windows\\system32\\drivers\\etc\\hosts", # Windows style
        "../../../../../../../../../../../../../../../../etc/passwd", # Deep traversal
        "foo/../../bar.txt" # Valid looking but still attempts to go up
    ]
    for path in traversal_paths:
        response = client.post('/image_to_diagram', data={'image_path': path})
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'error' in json_data
        assert json_data['error'] == "Invalid image path."

# --- Tests for convert_mermaid_to_png ---

@patch('app.subprocess.run')
@patch('builtins.open', new_callable=unittest_mock_open) # Mock open for .mmd and error .png
@patch('os.remove')
def test_convert_mermaid_to_png_success(mock_os_remove, mock_builtin_open, mock_subprocess_run, app_instance):
    """Test successful Mermaid to PNG conversion."""
    mock_subprocess_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with app_instance.app_context():
        result_path = flask_app.convert_mermaid_to_png("graph TD; A-->B;", "test_session", 0)

    expected_png_path = os.path.join(flask_app.config['GENERATED_MERMAID_IMAGES_FOLDER'], "session_test_session_iter_0.png")
    temp_mmd_path = os.path.join(flask_app.config['GENERATED_MERMAID_IMAGES_FOLDER'], "session_test_session_iter_0.mmd")

    assert result_path == expected_png_path
    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    assert args[0][0] == 'mmdc' # Check command
    assert args[0][2] == temp_mmd_path # Check input file path in command
    assert args[0][4] == expected_png_path # Check output file path in command

    mock_builtin_open.assert_called_with(temp_mmd_path, 'w', encoding='utf-8')
    mock_os_remove.assert_called_with(temp_mmd_path)


@patch('app.subprocess.run')
@patch('builtins.open', new_callable=unittest_mock_open)
@patch('os.remove')
def test_convert_mermaid_to_png_mmdc_error(mock_os_remove, mock_builtin_open, mock_subprocess_run, app_instance):
    """Test convert_mermaid_to_png when mmdc returns an error."""
    mock_subprocess_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="Error output", stderr="Syntax error in graph")

    temp_mmd_path = os.path.join(flask_app.config['GENERATED_MERMAID_IMAGES_FOLDER'], "session_test_session_err_iter_0.mmd")
    expected_png_path = os.path.join(flask_app.config['GENERATED_MERMAID_IMAGES_FOLDER'], "session_test_session_err_iter_0.png")

    with app_instance.app_context():
        result_path = flask_app.convert_mermaid_to_png("graph TD; A--B", "test_session_err", 0)

    assert result_path == expected_png_path
    # Check that the .mmd file was opened for writing, then the .png (error) file was opened for writing
    assert mock_builtin_open.call_args_list[0][0][0] == temp_mmd_path # .mmd write
    assert mock_builtin_open.call_args_list[1][0][0] == expected_png_path # .png error write

    mock_os_remove.assert_called_with(temp_mmd_path)


@patch('app.subprocess.run')
@patch('builtins.open', new_callable=unittest_mock_open)
@patch('os.remove')
def test_convert_mermaid_to_png_mmdc_not_found(mock_os_remove, mock_builtin_open, mock_subprocess_run, app_instance):
    """Test convert_mermaid_to_png when mmdc command is not found."""
    mock_subprocess_run.side_effect = FileNotFoundError("mmdc not found")

    temp_mmd_path = os.path.join(flask_app.config['GENERATED_MERMAID_IMAGES_FOLDER'], "session_test_session_fnf_iter_0.mmd")
    expected_png_path = os.path.join(flask_app.config['GENERATED_MERMAID_IMAGES_FOLDER'], "session_test_session_fnf_iter_0.png")

    with app_instance.app_context():
        result_path = flask_app.convert_mermaid_to_png("graph TD; A-->C", "test_session_fnf", 0)

    assert result_path == expected_png_path
    # Check that the .mmd file was opened for writing (it's written before subprocess.run is called)
    assert mock_builtin_open.call_args_list[0][0][0] == temp_mmd_path
    # Check that the .png (error) file was also opened for writing
    assert mock_builtin_open.call_args_list[1][0][0] == expected_png_path

    mock_os_remove.assert_called_with(temp_mmd_path)


@patch('app.call_vision_model_for_initial_diagram')
@patch('app.call_vision_model_for_comparison')
@patch('app.convert_mermaid_to_png')
def test_image_to_diagram_synchronous_success_fully_mocked(mock_convert, mock_compare, mock_initial, client, app_instance):
    mock_initial.return_value = "graph TD; Start-->Initial;"
    mock_convert.return_value = os.path.join(app_instance.config['GENERATED_MERMAID_IMAGES_FOLDER'], "dummy.png")
    mock_compare.return_value = {'is_final': True, 'updated_mermaid_diagram': "graph TD; Start-->Final;"}

    dummy_image_filename = "test_sync_image.png"
    dummy_image_path = os.path.join(app_instance.config['UPLOAD_FOLDER'], dummy_image_filename)

    # Ensure UPLOAD_FOLDER exists (it should be by app_instance fixture, but good practice)
    os.makedirs(app_instance.config['UPLOAD_FOLDER'], exist_ok=True)
    with open(dummy_image_path, 'w') as f: f.write("dummy image content")

    response = client.post('/image_to_diagram', data={
        'image_path': dummy_image_filename,
        'synchronous': 'true'
    })

    if os.path.exists(dummy_image_path):
        os.remove(dummy_image_path)
    # Clean up the dummy.png potentially created by mock_convert if it was a real path
    if os.path.exists(mock_convert.return_value):
         os.remove(mock_convert.return_value)


    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'finished'
    assert json_data['diagram'] == "graph TD; Start-->Final;"
    mock_initial.assert_called_once()
    assert mock_convert.call_count >= 1
    mock_compare.assert_called_once()
