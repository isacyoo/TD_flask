from clients import kvs_client

class RTSPStreamInfo:
    def __init__(self, info_dict):
        self.camera_id = info_dict['camera_id']
        self.stream_name = f"{self.camera_id}-stream"
        self.stream_url = info_dict['stream_url']
        self.data_retention = info_dict['data_retention']
        self.timezone = info_dict['timezone']

class KVSHandler:
    def __init__(self):
        self.client = kvs_client
    
    def check_if_stream_exists(self, stream_name):
        res = self.client.list_streams(
            MaxResults=1,
            StreamNameCondition={
                'ComparisonOperator': 'BEGINS_WITH',
                'ComparisonValue': stream_name
            }
        )

    def create_stream(self, stream_name, data_retention):
        self.client.create_stream(
            StreamName=stream_name,
            DataRetentionInHours=data_retention
        )
