# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from kubernetes import client

from polyaxon_k8s import constants as k8s_constants
from polyaxon_spawner.templates import constants
from polyaxon_spawner.templates import pods


def get_labels(name, project, role=None):
    labels = {'app': name, 'project': project}
    if role:
        labels['role'] = role
    return labels


def get_project_pod_spec(project,
                         name,
                         volume_mounts,
                         volumes,
                         command=None,
                         args=None,
                         ports=None,
                         resources=None,
                         env_vars=None,
                         restart_policy=None):
    """Pod spec to be used to create pods for project side: tensorboard, notebooks."""
    volume_mounts = volume_mounts or []
    volumes = volumes or []

    volume_mounts = volume_mounts or []
    volumes = volumes or []

    if resources.gpu:
        volume_mounts += pods.get_gpu_volume_mounts()
        volumes += pods.get_gpu_volumes()

    ports = [client.V1ContainerPort(container_port=port) for port in ports]

    container_name = constants.POD_CONTAINER_PROJECT_NAME.format(project=project, name=name)
    containers = [client.V1Container(name=container_name,
                                     image=constants.JOB_DOCKER_NAME,
                                     command=command,
                                     args=args,
                                     ports=ports,
                                     env=env_vars,
                                     resources=pods.get_resources(resources),
                                     volume_mounts=volume_mounts)]
    return client.V1PodSpec(restart_policy=restart_policy, containers=containers,
                            volumes=volumes)


def get_deployment_spec(namespace,
                        name,
                        project,
                        volume_mounts,
                        volumes,
                        command,
                        args,
                        ports,
                        resources=None,
                        role=None,
                        replicas=1):
    labels = get_labels(name, project, role)
    metadata = client.V1ObjectMeta(
        name=constants.DEPLOYMENT_NAME.format(project=project, name=name),
        labels=labels,
        namespace=namespace)
    pod_spec = get_project_pod_spec(project=project,
                                    name=name,
                                    volume_mounts=volume_mounts,
                                    volumes=volumes,
                                    command=command,
                                    args=args,
                                    resources=resources,
                                    ports=ports)
    template_spec = client.V1PodTemplateSpec(metadata=metadata, spec=pod_spec)
    return client.AppsV1beta1DeploymentSpec(replicas=replicas, template=template_spec)


def get_deployment(namespace,
                   name,
                   project,
                   volume_mounts,
                   volumes,
                   command,
                   args,
                   ports,
                   resources=None,
                   role=None,
                   replicas=1):
    labels = get_labels(name, project, role)
    metadata = client.V1ObjectMeta(
        name=constants.DEPLOYMENT_NAME.format(project=project, name=name),
        labels=labels,
        namespace=namespace)
    spec = get_deployment_spec(namespace=namespace,
                               name=name,
                               project=project,
                               volume_mounts=volume_mounts,
                               volumes=volumes,
                               command=command,
                               args=args,
                               ports=ports,
                               resources=resources,
                               role=role,
                               replicas=replicas)
    return client.AppsV1beta1Deployment(api_version=k8s_constants.K8S_API_VERSION_V1_BETA1,
                                        kind=k8s_constants.K8S_DEPLOYMENT_KIND,
                                        metadata=metadata,
                                        spec=spec)
