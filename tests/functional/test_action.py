from tests.conftest import test_client, TEST_CREDENTIALS, _create_header_token

def test_get_actions(test_client):
    response = test_client.get('/actions', headers=_create_header_token(test_client))
    assert response.status_code == 200
    assert response
    
def test_create_action(test_client):
    response = test_client.post('/action', json={"name": "test_action"}, headers=_create_header_token(test_client))
    assert response.status_code == 201
    assert response.data == b'Add action successful'
    
def test_apply_action_to_video(test_client):
    response = test_client.post('/action_to_video/test/1', headers=_create_header_token(test_client))
    assert response.status_code == 201
    assert response.data == b'Action 1 successfully applied to video test'
    
def test_apply_invalid_action_to_video(test_client):
    response = test_client.post('/action_to_video/test/100', headers=_create_header_token(test_client))
    assert response.status_code == 404
    assert response.data == b'Action id 100 not found'