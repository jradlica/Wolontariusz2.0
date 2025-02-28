#!/bin/bash

docker stop wolontariusz-app
docker rm wolontariusz-app
docker run --pull always -d -p 8000:8000 --name wolontariusz-app jradlica/wolontariusz:2.0
