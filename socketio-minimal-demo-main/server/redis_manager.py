import redis.asyncio as aioredis
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self, host='localhost', port=6379):
        logger.info(f"Initializing Redis manager - Host: {host}, Port: {port}")
        self.redis_client = aioredis.Redis(host=host, port=port, decode_responses=True)
        self.pubsub = None
    
    async def connect(self):
        """Initialize Redis connection and pubsub"""
        try:
            logger.info("Connecting to Redis server...")
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe('detection_updates', 'page_updates', 'page_results')
            logger.info("Successfully connected to Redis and subscribed to channels: detection_updates, page_updates, page_results")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def publish_detection_update(self, client_id: str, status: str, confidence: float, message: str):
        """Publish detection update to Redis"""
        data = {
            'type': 'DETECTION',
            'client_id': client_id,
            'status': status,
            'confidence': confidence,
            'message': message
        }
        try:
            result = await self.redis_client.publish('detection_updates', json.dumps(data))
            logger.debug(f"Published detection update to Redis - Client: {client_id}, Subscribers: {result}")
        except Exception as e:
            logger.error(f"Failed to publish detection update for client {client_id}: {e}")
            raise
    
    async def publish_page_count_update(self, client_id: str, total_pages: int):
        """Publish page count update to Redis"""
        data = {
            'type': 'PAGE_COUNT',
            'client_id': client_id,
            'total_pages': total_pages
        }
        try:
            result = await self.redis_client.publish('page_updates', json.dumps(data))
            logger.debug(f"Published page count update to Redis - Client: {client_id}, Pages: {total_pages}, Subscribers: {result}")
        except Exception as e:
            logger.error(f"Failed to publish page count update for client {client_id}: {e}")
            raise
    
    async def publish_page_result_update(self, client_id: str, page_num: int, result: dict):
        """Publish page result update to Redis"""
        data = {
            'type': 'PAGE_RESULT',
            'client_id': client_id,
            'page_num': page_num,
            'result': result
        }
        try:
            redis_result = await self.redis_client.publish('page_results', json.dumps(data))
            logger.debug(f"Published page result to Redis - Client: {client_id}, Page: {page_num}, Orientation: {result.get('orientation', 'unknown')}, Subscribers: {redis_result}")
        except Exception as e:
            logger.error(f"Failed to publish page result for client {client_id}, page {page_num}: {e}")
            raise
    
    async def listen_for_messages(self, callback):
        """Listen for Redis messages and call callback function"""
        logger.info("Starting Redis message listener...")
        message_count = 0
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    message_count += 1
                    try:
                        data = json.loads(message['data'])
                        logger.debug(f"Received Redis message #{message_count} on channel '{message['channel']}': {data.get('type', 'unknown')}")
                        await callback(data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode Redis message: {e}, Raw data: {message['data']}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            raise
    
    async def close(self):
        """Close Redis connections"""
        logger.info("Closing Redis connections...")
        try:
            if self.pubsub:
                await self.pubsub.close()
                logger.info("Redis pubsub connection closed")
            await self.redis_client.close()
            logger.info("Redis client connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
            raise