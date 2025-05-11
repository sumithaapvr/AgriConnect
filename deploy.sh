#!/bin/bash
    echo hello
    sh 'chmod +x build.sh'
    sh './build.sh'
    docker login -u sumithaapvr
    docker tag test1 sumithaapvr/agri
    docker push sumithaapvr/agri
    docker-compose up -d
    
