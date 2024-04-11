import flet as ft
import openai
import requests
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()
 
 #CURRENT PROMPT                         


speech_file_path = Path(__file__).parent /"assets/speech2.mp3"
conversation_context = ""
instruct = """
You provide support for emergency first responders. The user will provide you with the patient's location.
Use the following 4 step-by-step instructions to respond to user inputs. NB: NEVER OUTPUT THE FOUR STEPS TO THE USER:
Step 1 - You always start a conversation by asking for the patient's age and sex if not already provided by the user.
Step 2 - You then ask the user (first responder) to provide the complaints in 5 words or less if not already provided by the user.
Step 3 - You ask medically relevant follow-up questions if necessary to gain more clarity.
Step 4 - YOU OUTPUT THE TOP 5 MOST LIKELY MEDICAL DIAGNOSIS and then always provide immediate steps to manage the medical emergency.
Step 5 - YOU PROVIDE A LINK TO A YOUTUBE VIDEO THAT DEMONSTRATES AT LEAST ONE OF THE STEPS YOU OUTPUTTED FOR DEALING WITH THE MEDICAL EMERGENCY. 
NB: ENSURE THAT THE LINK TO THE VIDEO IS CORRECT AND APPROPRIATE FOR THE AGE OF THE PATIENT
Throughout the conversation, you will maintain a concise and prompt tone, focusing on directing the user to the most
appropriate care as quickly as possible. If the user inputs: "Thank you" or "Done" you end the conversation. An example conversation is as follows:

EXAMPLE:
USER INPUT: 50 years, male, sudden, central, chest pain
ASSISTANT:
Thank you for the information. The top five most likely medical emergencies in this scenario are:
1. Acute Coronary Syndrome
2. Acute Gastrooesophageal Reflux Disease
3. Pulmonary embolism
4. Heart failure
5. Oesophageal spasm

Immediate steps to manage medical emergency whilst transporting patient:
1. Ask the crowd to move away to allow proper ventilation
2. Check that airway is patent and clear it of every blockage
3. Give the person medication they may have been prescribed for the condition, if available.
4. Place the person in a comfortable, half-sitting position and continually reassure them.
5. Continuously monitor their breathing, pulse and responsiveness.

Here is the link to a YouTube video for further information:
https://youtu.be/gDwt7dD3awc?si=XTSUvfnTTx7Vktdf  

USER INPUT: Thank you!
ASSISTANT: All the best! The conversation has ended.
 """
#We might have to scrape the relevant YouTube videos and feed in to the model.
client = openai.OpenAI()


class Message():
    def __init__(self, user_name: str, text: str, message_type: str):
        self.user_name = user_name
        self.text = text
        self.message_type = message_type

class ChatMessage(ft.Row):
    def __init__(self, message: Message):
        super().__init__()
        self.vertical_alignment="start"
        self.controls=[
                ft.CircleAvatar(
                    content=ft.Text(self.get_initials(message.user_name)),
                    color=ft.colors.WHITE,
                    bgcolor=self.get_avatar_color(message.user_name),
                ),
                ft.Column(
                    [
                        ft.Text(message.user_name, weight="bold"),
                        ft.Text(message.text, selectable=True),
                    ],
                    tight=True,
                    spacing=5,
                ),
            ]

    def get_initials(self, user_name: str):
        if user_name:
            return user_name[:1].capitalize()
        else:
            return "Unknown"  # or any default value you prefer

    def get_avatar_color(self, user_name: str):
        colors_lookup = [
            ft.colors.AMBER,
            ft.colors.BLUE,
            ft.colors.BROWN,
            ft.colors.CYAN,
            ft.colors.GREEN,
            ft.colors.INDIGO,
            ft.colors.LIME,
            ft.colors.ORANGE,
            ft.colors.PINK,
            ft.colors.PURPLE,
            ft.colors.RED,
            ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(user_name) % len(colors_lookup)]

def main(page: ft.Page):
    page.horizontal_alignment = "stretch"
    page.title = "ER Assistant"
    page.platform == ft.PagePlatform.MACOS


    def join_chat_click(e):
        if not join_user_name.value:
            join_user_name.error_text = "Role cannot be blank!"
            join_user_name.update()
        else:
            page.session.set("user_name", join_user_name.value)
            page.dialog.open = False
            new_message.prefix = ft.Text(f"{join_user_name.value}: ")
            page.pubsub.send_all(Message(user_name=join_user_name.value, text=f"{join_user_name.value} has joined the chat.", message_type="login_message"))
            page.update()


    def stream_to_mp3_file (input_text): #output_file_path
        url = "https://api.openai.com/v1/audio/speech"
        data = {
        "model": "tts-1",
        "input": input_text,
        "voice": "alloy",
        "response_format": "mp3"
            }
        headers = {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
                }

        with requests.post(url, json=data, headers=headers, stream=True) as response:
            if response.status_code == 200:
                #with open(output_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=10):
                    yield chunk
                    audio1 = ft.Audio( src=chunk, autoplay=True)
                    page.overlay.append(audio1)
                        #f.write(chunk)
            else:
                print(f"Error: Received response code {response.status_code}")
                    
 #THIS PART CALLS THE OPEN AI API WHEN THE USER SENDS THE MESSAGE                           
    def send_message_click(e):
        global conversation_context
        if new_message.value != "":
            page.pubsub.send_all(Message(page.session.get("user_name"), new_message.value, message_type="chat_message"))
            conversation_context += new_message.value
            new_message.value = ""
            new_message.focus()
            response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
                        messages=[
                            {"role": "system", "content": instruct},
                            {"role": "user", "content": conversation_context}],
                        temperature=0.9)
            page.pubsub.send_all(Message(user_name="ER Assistant", text=response.choices[0].message.content, message_type="chat_message"))
            conversation_context += response.choices[0].message.content
            page.update()
            #stream_to_mp3_file("/Users/snoocode_2/Desktop/assets/output.mp3",conversation_context)
            #audio1 = ft.Audio( src=f"assets/output.mp3", autoplay=True)
        #page.overlay.append(audio1)

   
    def on_message(message: Message):
        if message.message_type == "chat_message":
            m = ChatMessage(message)
        elif message.message_type == "login_message":
            m = ft.Text(message.text, italic=True, color=ft.colors.BLACK45, size=12)
        chat.controls.append(m)
        page.update()

    page.pubsub.subscribe(on_message)

    # A dialog asking for a user display name
    join_user_name = ft.TextField(
        label="Enter your role to join the chat: e.g. EMT, Clinician, Bystander",
        autofocus=True,
        on_submit=join_chat_click,
    )
    page.dialog = ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Welcome!"),
        content=ft.Column([join_user_name], width=300, height=70, tight=True),
        actions=[ft.ElevatedButton(text="Join chat", on_click=join_chat_click)],
        actions_alignment="end",
    )

    # Chat messages
    chat = ft.ListView(
        expand=True,
        spacing=10,
        auto_scroll=True,
    )

    # A new message entry form
    new_message = ft.TextField(
        hint_text="Write a message...",
        autofocus=True,
        shift_enter=True,
        min_lines=1,
        max_lines=5,
        filled=True,
        expand=True,
        on_submit=send_message_click,
    )

    # Add everything to the page
    page.add(
        ft.Container(
            content=chat,
            border=ft.border.all(1, ft.colors.OUTLINE),
            border_radius=5,
            padding=10,
            expand=True,
        ),
        ft.Row(
            [
                new_message,
                ft.IconButton(
                    icon=ft.icons.SEND_ROUNDED,
                    tooltip="Send message",
                    on_click=send_message_click,
                ),
            ]
        ),
    )

ft.app(port=8550, target=main, assets_dir="assets")
#view=ft.WEB_BROWSER,