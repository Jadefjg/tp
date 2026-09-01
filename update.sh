git pull
docker build . -t tp
docker stop tp
docker rm tp
docker run --restart always --name tp -d --network subnet --ip 172.18.0.101 -e TORTOISE_ORM=extentions.db.TORTOISE_ORM -e TP_PORT=8080 -e TP_WOKERS=1 -e TP_RUNNER_PER_WORKER=20 -e TZ=Asia/Shanghai -v /home/ubuntu/data/media:/app/media tp
docker images tp -f "dangling=true" -q | xargs -x docker rmi