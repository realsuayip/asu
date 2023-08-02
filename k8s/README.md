# Kubernetes deployment configuration

This folder includes the complete Kubernetes stack for this project.

### Cheatsheet

```shell
# Deploy & remove deployments
kubectl apply -f k8s/
kubectl delete -f k8s/

# Create secrets
kubectl create secret generic asu-secrets --from-env-file=conf/prod/django.env
kubectl create secret generic postgres-secrets --from-env-file=conf/prod/postgres.env

# Restart deployments
kubectl rollout restart deployment --selector=py-context=django
kubectl rollout restart deployment --selector=py-context=celery
kubectl rollout restart deployment postgres

# Run & remove jobs
kubectl apply -f k8s/jobs/migrate.yaml
kubectl apply -f k8s/jobs/collectstatic.yaml
kubectl delete -f k8s/jobs/migrate.yaml
kubectl delete -f k8s/jobs/collectstatic.yaml
```
