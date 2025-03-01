#!/bin/bash

docker stop wolontariusz-app
docker rm wolontariusz-app
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=PL/ST=Mazowieckie/L=Warsaw/O=My Organization/OU=My Department/CN=localhost"
docker run --pull always -d -p 8000:8000 -v './key.pem:/app/key.pem' -v './cert.pem:/app/cert.pem' --name wolontariusz-app jradlica/wolontariusz:2.0
