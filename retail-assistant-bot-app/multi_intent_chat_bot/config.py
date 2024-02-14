#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import os
import openai
class DefaultConfig:
    """ Bot Configuration """
    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "xxxxxxxxxxxxxx8")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "xxxxxxxxxxxxxxxxxx")
    ai_search_url = "https://xxxxxxxxxxxxxx.search.windows.net"
    ai_search_key = "xxxxxxxxxxxxxx"
    ai_index_name = "contoso-retail-index"
    ai_semantic_config = "contoso-retail-config"
    az_db_server = "xxxxxxxxxxx.database.windows.net"
    az_db_database = "cdcsampledb"
    az_db_username = "xxxxxxxxxxx"
    az_db_password = "xxxxxxxxxxxxxxx"
    az_openai_key = "xxxxxxxxxxxxxxxxxx"
    az_openai_baseurl = "https://xxxxxxxxxxxxx.openai.azure.com/"
    az_openai_version = "2024-02-15-preview" # required for the assistants API
    deployment_name = "gpt-4-turbo"  # T
    assistant_id = "xxxxxxxxxxxx"