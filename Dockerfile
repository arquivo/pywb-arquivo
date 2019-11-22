ARG PYTHON=python:3.7.2

FROM $PYTHON

WORKDIR /pywb

COPY . ./

ARG PYWB_ENV=unframed

RUN cd $PYWB_ENV && pip install --no-cache-dir -r ./requirements.txt

WORKDIR $PYWB_ENV

ARG PORT=8080

ENV PORT $PORT

EXPOSE $PORT

CMD wayback -p $PORT
