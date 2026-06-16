import time

class QueryCache:
    def __init__(self, capacity=50):
        self.capacity = capacity
        self.cache = {}

    def get(self, query):
        q_lower = query.lower().strip()
        if q_lower in self.cache:
            item = self.cache.pop(q_lower)
            self.cache[q_lower] = item
            return item['response']
        return None

    def put(self, query, response):
        q_lower = query.lower().strip()
        if q_lower in self.cache:
            self.cache.pop(q_lower)
        elif len(self.cache) >= self.capacity:
            self.cache.pop(next(iter(self.cache)))
        self.cache[q_lower] = {
            'response': response,
            'timestamp': time.time()
        }
