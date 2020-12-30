# Collect metrics with Prometheus with push gateway

## Run Push Gateway

    docker pull prom/pushgateway
    docker run --restart=unless-stopped -d -p 9091:9091 prom/pushgateway

## Setup scraping target in Prometheus

```yaml
job_name: TempBatch
static_configs:
  - targets: ["raspberrypi:9091"]
honor_labels: true
```

## Run sprint with sendToPrometheus.py callback

Script will make one mesure and call script that send data to prometheus push gateway

    > python3 ./LYWSD03MMC.py --device XX:XX:XX:XX:XX:XX --round --debounce -call ./prometheus/sendToPrometheus.py -n living_room -c 1

## Grafana Dashboard

![grafana-dashboard](https://grafana.com/api/dashboards/12356/images/8223/image)

- Use dashboard_id `12356` or [read more how to import](https://grafana.com/grafana/dashboards/12356)
