import logging
import redis
import pickle

class InferenceService:
    def __init__(self,dao,web_svc):
        self.web_svc = web_svc
        self.dao = dao
        self.redis_ip = "127.0.0.1"
        self.redis_port = 6379

    async def load_redis_model(self):
        '''
        description: Loads the model dictionary from redis
        input: nil
        output: models dictionary from redis and hash for models dictionary
        '''
        logging.info("inference_svc: loading model from redis")
        r = redis.Redis(host=self.redis_ip, port=self.redis_port, db=0)
        model_data = r.get("model")
        model_hash_redis = r.get("model_hash")
        models = pickle.dumps(model_data)
        #model_hash = hashlib.md5().hexdigest()
        return models,model_hash_redis
