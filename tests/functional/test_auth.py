from tests.conftest import test_client, TEST_CREDENTIALS, _create_header_token

def test_login(test_client):
    response = test_client.post('/login', json=TEST_CREDENTIALS)
    assert response.status_code == 201
    assert response.json["id"] == "test"
    assert ["id", "name", "token"] == list(response.json.keys())
    
def test_login_with_invalid_credentials(test_client):
    response = test_client.post('/login', json={"id": "test", "password": "wrong"})
    assert response.status_code == 401
    assert response.data == b'Invalid login credentials'
    
def test_user_info_without_token(test_client):
    response = test_client.get('/user_info')
    assert response.status_code == 401
    assert response.json == {'msg': 'Missing Authorization Header'}
            
def test_user_info_with_token(test_client):
    response = test_client.get('/user_info', headers=_create_header_token(test_client))
    assert response.status_code == 200
    assert response.json == {"id": "test", "name": "test"}
    
def test_logout(test_client):
    response = test_client.get('/logout', headers=_create_header_token(test_client))
    assert response.status_code == 200
    assert response.data == b'Logout'
    
def test_reset_api_key(test_client):
    response = test_client.post('/reset_api_key', headers=_create_header_token(test_client))
    assert response.status_code == 201
    assert len(response.json["api_key"]) == 64
    
def test_get_api_key(test_client):
    response = test_client.get('/api_key', headers=_create_header_token(test_client))
    assert response.status_code == 200
    assert len(response.json["api_key"]) == 64