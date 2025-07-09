# Docker

``` bash
cd /d "D:\my_projects\talk-with-fews"
docker build -t talk-with-fews/api:0.0.1 -f docker\Dockerfile .
docker run --name talk-with-fews_0.0.1 -p 8000:8000 -t talk-with-fews/api:0.0.1
```
