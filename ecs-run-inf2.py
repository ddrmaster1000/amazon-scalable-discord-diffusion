import time
import numpy as np
from optimum.neuron import NeuronStableDiffusionXLPipeline

# Image Manipulation
import os
from PIL import Image

# Cloud Requirements
import boto3
import json
import requests
import random

TEST = False
REGION = requests.get('http://169.254.169.254/latest/meta-data/placement/region').content.decode("utf-8") 
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

    return r.ok

def messageResponse(customer_data):
    # Make the customer request readable
    message_response = ''
    readable_dict = {
        'prompt': 'Prompt',
        'negative_prompt': 'Negative Prompt',
        'seed': 'Seed',
        'steps': 'Steps',
        # 'sampler': 'Sampler',
        'model': 'Model'
    }

    for internal_var, readable in readable_dict.items():
        if internal_var in customer_data:
            message_response += f"{readable}: {customer_data[internal_var]}\n"
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

    return r.ok

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

def runStableDiffusion(pipe, user_inputs):
    # Run Stable Diffusion and create images in a grid.
    image_list = []
    user_prompts = [user_inputs['prompt']]*2
    for i in range(0,2):
        start_time = time.time()
        dev_images = pipe(prompt=user_prompts, num_inference_steps=int(user_inputs['steps']), guidance_scale=8.0, negative_prompt=user_inputs['negative_prompt']).images
        inf_time = time.time() - start_time
        print(f"[Inference Time per image] {np.round(inf_time, 2) / len(dev_images)} seconds.")
        for image_num in range(0, len(dev_images)):  
            image_list.append(dev_images[image_num])
    return image_list

def saveImage(image_list):
    my_grid = image_grid(image_list, 2, 2)
    my_grid.save('tmp.png', format="Png")
    return 'tmp.png'

def decideInputs(user_dict):
    default_dict = {
        'seed': random.randint(0,99999),
        'steps': 4,
        'negative_prompt': "",
        'model': "Jingya/lcm-sdxl-neuronx"
    }

    for internal_var, default in default_dict.items():
        if internal_var not in user_dict:
            user_dict[internal_var] = default
    return user_dict

def runMain():
    if TEST:
        message_dict = {
            'seed': "20",
            'prompt': 'an oil painting of a chocolate cake, amazing photography, creative, marble table',
            'steps': '4'
        }

    queue_long_poll = WAIT_TIME_SECONDS
    # Load SDXL into memory
    repo_id = "Jingya/lcm-sdxl-neuronx"
    pipe = NeuronStableDiffusionXLPipeline.from_pretrained(repo_id)

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
        successful_init_response = submitInitialResponse(message_dict['applicationId'], message_dict['interactionToken'], message_response)
        if successful_init_response:
            image_list = runStableDiffusion(pipe, message_dict)
            file_path = saveImage(image_list)
            successful_upload = picturesToDiscord(file_path, message_dict, message_response)
            cleanupPictures(file_path)
            ## Delete Message
            if successful_upload:
                deleteSQSMessage(QUEUE_URL, receipt_handle, message_dict['prompt'])

if __name__ == "__main__":
    runMain()