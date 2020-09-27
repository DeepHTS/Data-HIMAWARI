# Himawari data downloader

### python execution and debug
Python interpreter: Docker compose -> GPU, Dockerfile -> nonGPU

### jupyter
* Make container for jupyter or playground  
```
$ docker-compose run -p 8003:8003 --name=data-himawari_master_run data-himawari bash
```

* Settings on docker
```
# jupyter notebook --generate-config
# jupyter notebook password
```

* launch
```
# jupyter lab --ip=0.0.0.0 --port=8003 --allow-root
```
