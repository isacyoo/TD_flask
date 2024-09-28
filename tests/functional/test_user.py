from tests.conftest import test_client, TEST_CREDENTIALS, _create_header_token

def test_create_user(test_client):
    response = test_client.post('/user', json={"username": "test_user", "password": "test_password"})
    assert response.status_code == 201
    assert response.data == b'Successfully created user test_user'