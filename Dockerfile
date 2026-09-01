FROM python:3.9-buster
COPY . /app/
WORKDIR /app
RUN python -m pip install -r requirements.txt -i http://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
# -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
RUN sed -i 's/DEBUG=True/DEBUG=False/g' config.py
ENV PYTHONPATH=/app/:$PYTHONPATH
ENTRYPOINT [ "python", "app.py" ]
