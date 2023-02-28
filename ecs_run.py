from nataili.model_manager.compvis import CompVisModelManager
from nataili.stable_diffusion.compvis import CompVis
from nataili.util.logger import logger
import os
from PIL import Image

# Cloud Requirements
import boto3
import json
import requests
import random

TEST = False
REGION = boto3.session.Session().region_name
ssm = boto3.client('ssm', region_name=REGION)

# Create SQS client
QUEUE_URL = ssm.get_parameter(Name='/discord_diffusion/SQS_QUEUE')['Parameter']['Value']
SQS = boto3.client('sqs', region_name=REGION)

WAIT_TIME_SECONDS = 20

### SQS Functions ###
def getSQSMessage(queue_url, time_wait):
    # Receive message from SQS queue
    response = SQS.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        WaitTimeSeconds=time_wait,
    )

    try:
        message = response['Messages'][0]
    except KeyError:
        return None, None

    receipt_handle = message['ReceiptHandle']
    return message, receipt_handle

def deleteSQSMessage(queue_url, receipt_handle, prompt):
    # Delete received message from queue
    SQS.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )
    print(f'Received and deleted message: "{prompt}"')

def convertMessageToDict(message):
    cleaned_message = {}
    body = json.loads(message['Body'])
    for item in body:
        # print(item)
        cleaned_message[item] = body[item]['StringValue']
    return cleaned_message

def validateRequest(r):
    if not r.ok:
        print("Failure")
        print(r.text)
        # raise Exception(r.text)
    else:
        print("Success")
    return

### Discord required functions ###
def updateDiscordPicture(application_id, interaction_token, file_path):
    url = f'https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}/messages/@original'
    files = {'stable-diffusion.png': open(file_path,'rb')}
    r = requests.patch(url, files=files)
    validateRequest(r)
    return

def picturesToDiscord(file_path, message_dict, message_response):
    # Posts a follow up picture back to user on Discord

    # Initial Response is words.
    url = f"https://discord.com/api/v10/webhooks/{message_dict['applicationId']}/{message_dict['interactionToken']}/messages/@original"
    json_payload = {
        "content": f"*Completed your Sparkle!*```{message_response}```",
        "embeds": [],
        "attachments": [],
        "allowed_mentions": { "parse": [] },
    }
    r = requests.patch(url, json=json_payload)
    validateRequest(r)

    # Upload a picture
    files = {'stable-diffusion.png': open(file_path,'rb')}
    r = requests.patch(url, json=json_payload, files=files)
    validateRequest(r)

    return

def messageResponse(customer_data):
    # Make the customer request readable
    message_response = ''
    readable_dict = {
        'prompt': 'Prompt',
        'neg_prompt': 'Negative Prompt',
        'seed': 'Seed',
        'steps': 'Steps',
        'sampler': 'Sampler'
    }

    for internal_var, readable in readable_dict.items():
        if internal_var in customer_data:
            message_response += f"\{readable}: {customer_data[internal_var]}"
    return message_response

def submitInitialResponse(application_id, interaction_token, message_response):
    # Posts a follow up picture back to user on Discord
    url = f'https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}/messages/@original'
    json_payload = {
        "content": f"Processing your Sparkle```{message_response}```",
        "embeds": [],
        "attachments": [],
        "allowed_mentions": { "parse": [] },
    }
    r = requests.patch(url, json=json_payload, )
    validateRequest(r)

    return

def cleanupPictures(path_to_file):
    # Clean up file(s) created during creation.
    os.remove(path_to_file)
    return

### Stable Diffusion functions ###
def image_grid(imgs, rows, cols):
    assert len(imgs) == rows*cols

    w, h = imgs[0].size
    grid = Image.new('RGB', size=(cols*w, rows*h))

    for i, img in enumerate(imgs):
        grid.paste(img, box=(i%cols*w, i//cols*h))
    return grid

def runStableDiffusion(compvis, user_inputs):
    # Run Stable Diffusion and create images in a grid.
    image_list = []
    for my_seed in range(int(user_inputs['seed']),int(user_inputs['seed']) + 4):
        compvis.generate(
            prompt=f"{user_inputs['prompt']} ### {user_inputs['neg_prompt']}",
            sampler_name=user_inputs['sampler'],
            ddim_steps=int(user_inputs['steps']),
            seed=my_seed,
            save_individual_images=False
        )    
    image_list = [i["image"] for i in compvis.images]
    return image_list

def saveImage(image_list):
    my_grid = image_grid(image_list, 2, 2)
    my_grid.save('tmp.png', format="Png")
    return 'tmp.png'

def decideInputs(user_dict):
    if 'seed' not in user_dict:
        user_dict['seed'] = random.randint(0,99999)

    if 'steps' not in user_dict:
        user_dict['steps'] = 16

    if 'neg_prompt' not in user_dict:
        user_dict['neg_prompt'] = ""

    if 'sampler' not in user_dict:
        user_dict['sampler'] = 'k_euler_a'
    return user_dict

def runMain():
    mm = CompVisModelManager()
    # The model to use for the generation.
    model = "stable_diffusion_2.1_512"
    mm.load(model)

    compvis = CompVis(
        model=mm.loaded_models[model],
        model_name=model,
        output_dir="output_dir",
        disable_voodoo=True,
        filter_nsfw=False,
        safety_checker=None,
    )
    if TEST:
        message_dict = {
            'seed': "20",
            'prompt': 'a chocolate cake',
            'sampler': 'k_euler_a',
            'steps': '25'
        }

    queue_long_poll = WAIT_TIME_SECONDS
    # Get Message from Queue
    while True:
        print("Waiting for next message from Queue...")
        message, receipt_handle = getSQSMessage(QUEUE_URL, WAIT_TIME_SECONDS)

        if not message:
            ## Wait for new message or timeout and exit
            while not message:
                message, receipt_handle = getSQSMessage(QUEUE_URL, queue_long_poll)
                if message:
                    break

        ## Run stable Diffusion
        print("Found a message! Running Stable Diffusion")
        message_dict = convertMessageToDict(message)
        message_dict = decideInputs(message_dict)
        message_response = messageResponse(message_dict)
        print(message_response)
        submitInitialResponse(message_dict['applicationId'], message_dict['interactionToken'], message_response)

        image_list = runStableDiffusion(compvis, message_dict)
        file_path = saveImage(image_list)
        picturesToDiscord(file_path, message_dict, message_response)
        cleanupPictures(file_path)
        ## Delete Message
        deleteSQSMessage(QUEUE_URL, receipt_handle, message_dict['prompt'])

if __name__ == "__main__":
    runMain()
