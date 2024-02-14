#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import os
import openai
class DefaultConfig:
    """ Bot Configuration """
    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "xxxxxxxxxxxxx")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "xxxxxxxxxxxxxxxx")
    ai_search_url = "https://xxxxxxxxxxxxx.search.windows.net"
    ai_search_key = "xxxxxxxxxxxxxx"
    ai_index_name = "contoso-retail-index"
    ai_semantic_config = "contoso-retail-config"
    az_db_server = "xxxxxxxxxx.database.windows.net"
    az_db_database = "cdcsampledb"
    az_db_username = "xxxxxxxxxxxx"
    az_db_password = "xxxxxxxxxxx"
    az_openai_key = "xxxxxxxxxxxxxx"
    az_openai_baseurl = "https://xxxxxxxxxxxxxx.openai.azure.com/"
    az_openai_version = "2024-02-15-preview" # required for the assistants API
    deployment_name = "gpt-4-turbo"  # T
    assistant_id = "xxxxxxxxxxxxxxxxxxxxx6"