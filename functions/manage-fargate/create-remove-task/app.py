import boto3
import json
import os

dynamodb = boto3.client('dynamodb')
ecs = boto3.client('ecs')

def lambda_handler(event, context):
    
    TABLE_JOBS = os.environ['TABLE_JOBS']
    
    CLUSTER_NAME = os.environ['CLUSTER_NAME']
    TASK_DEFINITION = os.environ['TASK_DEFINITION']
    TASK_ROLE_ARN = os.environ['TASK_ROLE_ARN']
    SUBNET_ID_01 = os.environ['SUBNET_ID_01']
    SUBNET_ID_02 = os.environ['SUBNET_ID_02']
    SECURITY_GROUP_ID = os.environ['SECURITY_GROUP_ID']
    
    
    create_task = False
    
    print(json.dumps(event))
    try:
        records = event['Records']
        for record in records:
            print(json.dumps(record))
            if 'NewImage' in record['dynamodb'] and 'active' in record['dynamodb']['NewImage'] and  record['dynamodb']['NewImage']['active']['BOOL']==True:
                if 'taskArn' in record['dynamodb']['NewImage'] and record['dynamodb']['NewImage']['taskArn']!="":
                    create_task = False
                else:
                    create_task = True
                
                if create_task: 
                    response = ecs.run_task(
                        cluster=CLUSTER_NAME,
                        launchType='FARGATE',
                        taskDefinition=TASK_DEFINITION.split('/')[1],
                        overrides={
                            'containerOverrides': [
                                {   'name': 'container', 
                                    'environment': [
                                        { 'name': 'TABLE_JOBS', 'value': TABLE_JOBS }
                                    ] 
                                
                                }
                            ],
                            'taskRoleArn':TASK_ROLE_ARN
                        },
                        networkConfiguration={
                            'awsvpcConfiguration': {
                                        'subnets': [
                                            SUBNET_ID_01,SUBNET_ID_02
                                        ],
                                        'securityGroups': [
                                            SECURITY_GROUP_ID
                                        ],
                                        'assignPublicIp': 'ENABLED'
                                    }
                        }
                    )
                    
                    print(response)
                    print(response['tasks'][0]['containers'][0]['taskArn'])
                    
                    response = dynamodb.update_item(
                        TableName=TABLE_JOBS,
                        Key=record['dynamodb']['Keys'],
                        AttributeUpdates={
                            'taskArn': { 'Value': { 'S': response['tasks'][0]['containers'][0]['taskArn'] }, 'Action' : 'PUT' }
                        }
                    )
                
            elif 'NewImage' in record['dynamodb'] and 'active' in record['dynamodb']['NewImage'] and  record['dynamodb']['NewImage']['active']['BOOL']==False and 'taskArn' in record['dynamodb']['NewImage']:
                
                response = ecs.stop_task(
                    cluster=CLUSTER_NAME,
                    task=record['dynamodb']['NewImage']['taskArn']['S'],
                    reason='Stop task'
                )
                
                response = dynamodb.update_item(
                    TableName=TABLE_JOBS,
                    Key=record['dynamodb']['Keys'],
                    AttributeUpdates={
                        'taskArn': { 'Action' : 'DELETE' }
                    }
                )
                
            else:
                print("Different change")
        return True
    except Exception as e:
        print(e)
        raise e
