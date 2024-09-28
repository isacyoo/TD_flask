from server import create_app
import pytest

TEST_CREDENTIALS = {"id": "test", "password": "test"}

@pytest.fixture(scope='module')
def test_client():
    app, _ = create_app()
    app.testing = True
    with app.test_client() as testing_client:
        with app.app_context():
            yield testing_client
            
def _create_header_token(test_client):
    response = test_client.post('/login', json=TEST_CREDENTIALS)
    return {"Authorization": f"Bearer {response.json['token']}"}  
