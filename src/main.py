#Vehicle Detection
import cv2

#IBM IOT connectioon
import wiotp.sdk.device

#IBM COS
import ibm_boto3

#IBM Cloudant
from ibm_botocore.client import Config, ClientError
from ibmcloudant.cloudant_v1 import CloudantV1
from ibmcloudant import CouchDbSessionAuthenticator
from ibm_cloud_sdk_core.authenticators import BasicAuthenticator

#Clarifai
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import service_pb2_grpc
stub = service_pb2_grpc.V2Stub(ClarifaiChannel.get_grpc_channel())
from clarifai_grpc.grpc.api import service_pb2, resources_pb2
from clarifai_grpc.grpc.api.status import status_code_pb2

#Miscellaneous
import time
import random
import datetime

#IOT device connection
myConfig = { 
    "identity": {
        "orgId": "j8rgpm",
        "typeId": "First_Device",
        "deviceId":"123"
    },
    "auth": {
        "token": "First_Device_123"
    }
}


    
# Constants for IBM COS values
COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" 
COS_API_KEY_ID = "78NLlHvfEUxheNWr4jehqUGifUPewWVaPrk3N2HXaMKy" 
COS_INSTANCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/abaf1723c9c84a148e04f11a73d2442a:880edc7f-ce14-4df9-8545-5c592c737b87::" 

# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

authenticator = BasicAuthenticator('apikey-v2-10xypw9nevga82oqb993uwcfdqgl748fcoiznj3jfrzn', '3fb54d29a2d64e40f7a0657467d33a27')
service = CloudantV1(authenticator=authenticator)
service.set_service_url('https://apikey-v2-10xypw9nevga82oqb993uwcfdqgl748fcoiznj3jfrzn:3fb54d29a2d64e40f7a0657467d33a27@c6a728a6-a633-4d59-a8e9-c06a612f8176-bluemix.cloudantnosqldb.appdomain.cloud')
client = wiotp.sdk.device.DeviceClient(config=myConfig, logHandlers=None)
client.connect()

#Image upload to COS bucket
bucket = "rohanbucket"
def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))        
        part_size = 1024 * 1024 * 5        
        file_threshold = 1024 * 1024 * 15        
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )        
        with open(file_path, "rb") as file_data:
            cos.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )
        print("Transfer for {0} Complete!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))


   
video = cv2.VideoCapture('cars.avi')
# Clarifai Authentication
metadata = (('authorization', 'Key f9c413355966419bbd1b0e0125a9a5bc'),)

#Initial Conditions
print("Door is Closed")
print("Light is Off")

def myCommandCallback(cmd):
    m=cmd.data['command']
    print(m,"\n")    
    
    
while True:
    distance=random.randint(5,500) # random distance values from 5 to 500 meters
    check,frame=video.read()
    frame = cv2.resize(frame, (600,400))
    if (distance<=15): #picture is sent to clarifai when distance is less than 15 meters        
        myData={'distance':distance}
        print(myData)
        client.publishEvent(eventId="status", msgFormat="json", data=myData, qos=0, onPublish=None)        
        picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M-%S")
        path="D:\\rohan\\Personal\\Courses\\IOT\\Final Project\\pics\\" +picname + ".jpg"
        cv2.imwrite(picname+".jpg",frame) # Images are stored locally in a folder
        time.sleep(1)
        with open(path, "rb") as f:
            file_bytes = f.read()
  
        request = service_pb2.PostModelOutputsRequest(
            # This is the model ID of a publicly available General model. You may use any other public or custom model ID.
            model_id='aaa03c23b3724a16a56b629203edc62c',
            inputs=[
              resources_pb2.Input(data=resources_pb2.Data(image=resources_pb2.Image(base64=file_bytes)))
            ])
        response = stub.PostModelOutputs(request, metadata=metadata)

        if response.status.code != status_code_pb2.SUCCESS:
            raise Exception("Request failed, status code: " + str(response.status.code))
        a= []
        for concept in response.outputs[0].data.concepts:
            if(concept.value > 0.8):
                a.append(concept.name)      
        t=1
        for i in a:
            if(i == "car" or i == "vehicle" or i=="bike"):        
                print("Vehicle is detected\n")
                print("Door is open\nLight is On")
                #if vehicle is detected document is uploaded to cloudant database
                multi_part_upload(bucket, picname+'.jpg', picname+'.jpg')
                json_document={"link":COS_ENDPOINT+'/'+bucket+'/'+picname+'.jpg'}                
                response = service.post_document(db='sample', document=json_document).get_result()
                break    

    Key=cv2.waitKey(1)    
    client.commandCallback = myCommandCallback
    
client.disconnect()
