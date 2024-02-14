from botbuilder.core import ActivityHandler, ConversationState, TurnContext, UserState
from botbuilder.schema import ChannelAccount

# from rpay_chat_bot.user_profile import UserProfile
from data_models.user_profile import UserProfile
from data_models.conversation_data import ConversationData
import time
from datetime import datetime
from openai import AzureOpenAI
import sys
from config import DefaultConfig
import json
import os
from botbuilder.schema import HeroCard, CardAction, ActionTypes, CardImage, Attachment, Activity, ActivityTypes
from botbuilder.core import TurnContext, MessageFactory, CardFactory
import base64
import pyodbc
import inspect
import requests
import openai
import io
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from PIL import Image
from IPython.display import display
import base64



class StateManagementBot(ActivityHandler):

    connection = None
    user_response_system_prompt = None
    client =  None
    assistant = None

    def init_meta_prompt() -> any:
        # print("init")
        # read all lines from a text file
        
        with open("metaprompt-1.txt", "r") as file:
            data = file.read().replace("\n", "")
        return data


    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        if conversation_state is None:
            raise TypeError(
                "[StateManagementBot]: Missing parameter. conversation_state is required but None was given"
            )
        if user_state is None:
            raise TypeError(
                "[StateManagementBot]: Missing parameter. user_state is required but None was given"
            )

        self.conversation_state = conversation_state
        self.user_state = user_state
        self.config =  DefaultConfig()

        
        # Create Azure OpenAI client
        if StateManagementBot.client is None:
            print("Creating Azure OpenAI client....")   
            StateManagementBot.client = AzureOpenAI(
                api_key=self.config.az_openai_key,
                azure_endpoint=self.config.az_openai_baseurl,
                api_version=self.config.az_openai_version
            )

        # Run the following lines of code to create a new Assistant and get the assistant id
        #     StateManagementBot.assistant = StateManagementBot.client.beta.assistants.create(
        #     name="Contoso Retail Employee Assistant",
        #     instructions=StateManagementBot.init_meta_prompt(),
        #     tools=StateManagementBot.tools,
        #     model=self.config.deployment_name
        # )

            # print('assistant created!',StateManagementBot.assistant.id)
            # # display information about the assistant
            # print(StateManagementBot.assistant.model_dump_json(indent=2))

        self.conversation_data_accessor = self.conversation_state.create_property(
            "ConversationData"
        )
        self.user_profile_accessor = self.user_state.create_property("UserProfile")
        if StateManagementBot.connection is None:
            print("Connecting to database....")
            l_connection = pyodbc.connect('Driver={ODBC Driver 18 for SQL Server};SERVER=' + self.config.az_db_server + ';DATABASE=' + self.config.az_db_database + ';UID=' + self.config.az_db_username + ';PWD=' + self.config.az_db_password)
            StateManagementBot.connection = l_connection
            print("Connection to database established")

    async def on_message_activity(self, turn_context: TurnContext):
        # Get the state properties from the turn context.
        user_profile = await self.user_profile_accessor.get(turn_context, UserProfile)
        conversation_data = await self.conversation_data_accessor.get(
            turn_context, ConversationData
        )

        if user_profile.name is None:
            # First time around this is undefined, so we will prompt user for name.
            if conversation_data.prompted_for_user_name:
                # Set the name to what the user provided.
                user_profile.name = turn_context.activity.text

                conversation_data.chat_history = StateManagementBot.init_meta_prompt()

                # Acknowledge that we got their name.
                await turn_context.send_activity(
                    f"Thanks { user_profile.name }. Let me know how can I help you today"
                )

                # Reset the flag to allow the bot to go though the cycle again.
                conversation_data.prompted_for_user_name = False
            else:
                # Prompt the user for their name.
                await turn_context.send_activity("I am your AI Employee Assistant for Contoso Retail. I can help you quickly get to it!"+\
                                                  "Can you help me with your name?")

                # Set the flag to true, so we don't prompt in the next turn.
                conversation_data.prompted_for_user_name = True
        else:
            # Add message details to the conversation data.
            conversation_data.timestamp = self.__datetime_from_utc_to_local(
                turn_context.activity.timestamp
            )
            conversation_data.channel_id = turn_context.activity.channel_id

            l_thread = conversation_data.thread

            if conversation_data.thread is None:
                # Create a thread
                conversation_data.thread = StateManagementBot.client.beta.threads.create()
                l_thread = conversation_data.thread
                # Threads have an id as well
                print('Session not available for this user, creating one!')
                print("Created thread bearing Thread id: ", conversation_data.thread.id)

            

            # Add a user question to the thread
            message = StateManagementBot.client.beta.threads.messages.create(
                thread_id=l_thread.id,
                role="user",
                content=turn_context.activity.text
            )
            print("Created message bearing Message id: ", message.id)

            # Show the messages
            thread_messages = StateManagementBot.client.beta.threads.messages.list(l_thread.id)
            print('list of all messages: \n',thread_messages.model_dump_json(indent=2))


            # create a run 
            run = StateManagementBot.client.beta.threads.runs.create(
                thread_id=l_thread.id,
                assistant_id=self.config.assistant_id # use the assistant id defined in the first cell
            )
            print('called thread run ...')

            # wait for the run to complete
            run = StateManagementBot.wait_for_run(run, l_thread.id)
            print('run has completed, extracting results ...')
            # show information about the run
            # should indicate that run status is requires_action
            # should contain information about the tools to call
            print('the thread has run!! \n',run.model_dump_json(indent=2))

            # we only check for required_action here
            # required action means we need to call a tool
            if run.required_action:
                # get tool calls and print them
                # check the output to see what tools_calls contains
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                print("Tool calls:", tool_calls)

                # we might need to call multiple tools
                # the assistant API supports parallel tool calls
                # we account for this here although we only have one tool call
                tool_outputs = []
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    if 'get_consignment_delivery_status' == func_name:
                        result = StateManagementBot.get_consignment_delivery_status(**arguments)
                    elif 'perform_search_based_qna' == func_name:
                        result = StateManagementBot.perform_search_based_qna(**arguments)

                    # append the results to the tool_outputs list
                    # you need to specify the tool_call_id so the assistant knows which tool call the output belongs to
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(result)
                    })

                print("Tool outputs:", tool_outputs)

                # now that we have the tool call outputs, pass them to the assistant
                run = StateManagementBot.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=l_thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )

                print("Tool outputs submitted")
                # now we wait for the run again
                run = StateManagementBot.wait_for_run(run, l_thread.id)
                print('run has completed, extracting results ...')
            else:
                print("No tool calls identified. Checking for Code interpreter runs \n")
                # await turn_context.send_activity(
                #         f"{ user_profile.name } : sorry! I could not find any information for you. Please try again later."
                #     )
                # return
                # dump the messages on the thread again
                # messages = StateManagementBot.client.beta.threads.messages.list(
                # thread_id=l_thread.id
                # )

                # print(messages.model_dump_json(indent=2))

            # show information about the run
            print("Run information:")
            print("----------------")
            print(run.model_dump_json(indent=2), "\n")

            # now print all messages in the thread
            print("Messages in the thread:")
            print("-----------------------")
            messages = StateManagementBot.client.beta.threads.messages.list(thread_id=l_thread.id)
            print(messages.model_dump_json(indent=2))



            messages_json = json.loads(messages.model_dump_json())
            print('response messages_json>\n',messages_json)
            action_response_to_user = ''
            file_content = None
            file_id = ''
            # for item in reversed(messages_json['data']):
            #     # Check the content array
            #     for content in reversed(item['content']):
            #         # If there is text in the content array, print it
            #         if 'text' in content:
            #             print(StateManagementBot.role_icon(item["role"]),content['text']['value'], "\n")
            #             action_response_to_user = content['text']['value'] + "\n"
            #         # If there is an image_file in the content, print the file_id
            #             if 'image_file' in content:
            #                 print("Image ID:" , content['image_file']['file_id'], "\n")
            #                 file_id = content['image_file']['file_id']
            #                 file_content = StateManagementBot.client.files.content(file_id)
            #                 image_data_bytes = file_content.read()
            #                 with open("./"+file_id+".png", "wb") as file:
            #                     file.write(image_data_bytes)
            #             else:
            #                 print("No image file found in the content")
            counter = 0
            for item in messages_json['data']:
                # Check the content array
                for content in item['content']:
                    # If there is text in the content array, print it
                    if 'text' in content:
                        print(StateManagementBot.role_icon(item["role"]),content['text']['value'], "\n")
                        action_response_to_user = content['text']['value'] + "\n"
                    # If there is an image_file in the content, print the file_id
                    if 'image_file' in content:
                        print("Image ID:" , content['image_file']['file_id'], "\n")
                        file_id = content['image_file']['file_id']
                        file_content = StateManagementBot.client.files.content(file_id)
                        image_data_bytes = file_content.read()
                        with open("./"+file_id+".png", "wb") as file:
                            file.write(image_data_bytes)
                counter += 1
                if counter == 1:
                    break

            if file_content is not None:
                reply = Activity(type=ActivityTypes.message)
                reply.text = action_response_to_user
                file_path = file_id+".png"
                with open(file_path, "rb") as in_file:
                    base64_image = base64.b64encode(in_file.read()).decode()

                # Create an attachment with the base64 image
                attachment = Attachment(
                    name=file_id+".png",
                    content_type="image/png",
                    content_url=f"data:image/png;base64,{base64_image}"
                )
                reply.attachments = [attachment]
                await turn_context.send_activity(reply)
            else:
                await turn_context.send_activity(
                        f"{ user_profile.name } : { action_response_to_user }"
                    )
            return
    
    def role_icon(role):
        if role == "user":
            return "👤"
        elif role == "assistant":
            return "🤖"

    # function returns the run when status is no longer queued or in_progress
    def wait_for_run(run, thread_id):
        while run.status == 'queued' or run.status == 'in_progress':
            run = StateManagementBot.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
            )
            print("Run status:", run.status)
            time.sleep(0.5)

        return run
    
    def get_consignment_delivery_status(order_id):
        response_message = 'The order status is: '
        cursor = None
        # if order_id is None:
        #     return "Sure, I will help you with the status of your order. Can you please the order id of the consignment?"
        try:
            cursor = StateManagementBot.connection.cursor()
            cursor.execute('SELECT * FROM dbo.consignments where OrderID = ?', order_id)
        except Exception as e:
            print(e)
            print("Error in database query execution")
        
        for row in cursor:
            response_message += str(row) + "\n"

        print('order status response from database - ',response_message)
        return response_message

    

    def perform_search_based_qna(query):
        config = DefaultConfig()
        service_endpoint = config.ai_search_url
        index_name = config.ai_index_name
        key = config.ai_search_key
        semantic_config = config.ai_semantic_config

        credential = AzureKeyCredential(key)
        client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=credential)
        results = list(
            client.search(
                search_text=query,
                query_type="semantic",
                semantic_configuration_name=semantic_config
            )
        )
        response = ''
        for result in results:
            response += result['content'] + "\n"
        print('search response documents - ',response)
        return response

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)

        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    def __datetime_from_utc_to_local(self, utc_datetime):
        now_timestamp = time.time()
        offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(
            now_timestamp
        )
        result = utc_datetime + offset
        return result.strftime("%I:%M:%S %p, %A, %B %d of %Y")
    

    tools = [
        {
            "function": {
                "name": "get_consignment_delivery_status",
                "description": "fetch real time delivery status update of consignments in an order, like expected delivery date, current location, status, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "number",
                            "description": "The order id of the consignment",
                        }
                    },
                    "required": [
                        "order_id"
                    ]
                }
            },
            "type": "function"
        },
        {
            "function": {
                "name": "perform_search_based_qna",
                "description": "Seek general assistance or register complaint with the AI assistant. This requires performing a search based QnA on the query provided by the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to seek assistance for"
                        }
                    },
                    "required": [
                        "query"
                    ]
                }
            },
            "type": "function"
        }, 
            {
                "type": "code_interpreter",  # should be set to retrieval but that is not supported yet; required or file_ids will throw error
            }
    ]

    available_functions = {
    "get_consignment_delivery_status": get_consignment_delivery_status,
    "perform_search_based_qna": perform_search_based_qna
    }


    # helper method used to check if the correct arguments are provided to a function
    def check_args(function, args):
        print('checking function parameters')
        sig = inspect.signature(function)
        params = sig.parameters
        # Check if there are extra arguments
        for name in args:
            if name not in params:
                return False
        # Check if the required arguments are provided
        for name, param in params.items():
            if param.default is param.empty and name not in args:
                return False

        return True


