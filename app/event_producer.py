"""
Класс для отправки событий в RabbitMQ.
"""

import pika
import json
import logging

logger = logging.getLogger(__name__)


class EventProducer:
    """Класс для отправки сообщений в RabbitMQ"""

    def __init__(self, queue_name="file_upload_notifications"):
        self.queue_name = queue_name
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=queue_name, durable=True)
        except Exception as e:
            logger.error(f"Ошибка подключения к RabbitMQ: {e}")
            self.connection = None

    def send_event(self, message: dict):
        """Отправляет сообщение в очередь RabbitMQ"""
        if not self.connection:
            logger.error(
                "Подключение к RabbitMQ отсутствует, сообщение не отправлено."
            )
            return

        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Устойчивые сообщения
                ),
            )
            logger.info(f"Отправлено сообщение в RabbitMQ: {message}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения в RabbitMQ: {e}")

    def close(self):
        """Закрывает подключение к RabbitMQ"""
        if self.connection:
            self.connection.close()
