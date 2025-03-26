#!/bin/bash

TAG=ecs/backend
ECR_URI=524449828506.dkr.ecr.ap-southeast-2.amazonaws.com
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin $ECR_URI
docker build -t $TAG .
docker tag $TAG:latest $ECR_URI/$TAG:latest
docker push $ECR_URI/$TAG:latest
