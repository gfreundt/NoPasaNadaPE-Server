import os
from datetime import datetime as dt
from flask import request, jsonify

from src.updates import get_records_to_update, get_recipients
from src.utils.constants import SQL_TABLES, NETWORK_PATH, UPDATER_TOKEN
from src.comms import craft_messages, send_messages_and_alerts, craft_alerts
from src.maintenance import maintenance


def alta(self):

    return
