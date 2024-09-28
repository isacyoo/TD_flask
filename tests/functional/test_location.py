from tests.conftest import test_client, TEST_CREDENTIALS, _create_header_token

def test_get_location(test_client):
    response = test_client.get('/locations', headers=_create_header_token(test_client))
    assert response.status_code == 200
    assert response.json == [{"id": 1, "name": "test"}]
    
def test_get_location_id(test_client):
    response = test_client.get('/location_id/test', headers=_create_header_token(test_client))
    assert response.status_code == 200
    assert response.json == {"id": 1, "name": "test"}
    
def test_get_invalid_location_id(test_client):
    response = test_client.get('/location_id/invalid', headers=_create_header_token(test_client))
    assert response.status_code == 404
    assert response.data == b'Location id invalid not found'