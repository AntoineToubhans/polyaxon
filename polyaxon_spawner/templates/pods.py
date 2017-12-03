# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import six
import uuid

from kubernetes import client

from polyaxon_schemas.exceptions import PolyaxonConfigurationError
from polyaxon_schemas.utils import TaskType

from polyaxon_k8s import constants as k8s_constants

from polyaxon_spawner.templates import constants
from polyaxon_spawner.templates.persistent_volumes import get_vol_path


def get_gpu_volume_mounts():
    return [
        client.V1VolumeMount(name='bin', mount_path='/usr/local/nvidia/bin'),
        client.V1VolumeMount(name='lib', mount_path='/usr/local/nvidia/lib'),
    ]


def get_gpu_volumes():
    return [
        client.V1Volume(name='bin',
                        host_path=client.V1HostPathVolumeSource(path='/usr/local/nvidia/bin')),
        client.V1Volume(name='lib',
                        host_path=client.V1HostPathVolumeSource(path='/usr/local/nvidia/lib')),
    ]


def get_volume_mount(volume, run_type):
    volume_name = constants.VOLUME_NAME.format(vol_name=volume)
    return client.V1VolumeMount(name=volume_name,
                                mount_path=get_vol_path(volume, run_type))


def get_volume(volume):
    vol_name = constants.VOLUME_NAME.format(vol_name=volume)
    volc_name = constants.VOLUME_CLAIM_NAME.format(vol_name=volume)
    pv_claim = client.V1PersistentVolumeClaimVolumeSource(claim_name=volc_name)
    return client.V1Volume(name=vol_name, persistent_volume_claim=pv_claim)


def get_resources(resources):
    """Create resources requirements.

    Args:
        resources: `PodResourcesConfig`

    Return:
        `V1ResourceRequirements`
    """
    limits = {}
    requests = {}
    if resources is None:
        return None
    if resources.cpu:
        if resources.cpu.limits:
            limits['cpu'] = resources.memory.limits
        if resources.cpu.request:
            limits['cpu'] = resources.memory.request

    if resources.cpu:
        if resources.cpu.limits:
            limits['memory'] = resources.memory.limits
        if resources.cpu.request:
            limits['memory'] = resources.memory.request

    if resources.gpu:
        if resources.gpu.limits:
            limits['alpha.kubernetes.io/nvidia-gpu'] = resources.gpu.limits
        if resources.cpu.request:
            limits['alpha.kubernetes.io/nvidia-gpu'] = resources.gpu.request
    return client.V1ResourceRequirements(limits=limits, requests=requests)


class PodManager(object):
    def __init__(self,
                 namespace,
                 project,
                 experiment=None,
                 job_container_name=None,
                 job_docker_image=None,
                 sidecar_container_name=None,
                 sidecar_docker_image=None,
                 role_label=None,
                 type_label=None,
                 ports=None,
                 use_sidecar=False,
                 sidecar_config=None):
        self.namespace = namespace
        self.project = project
        self.experiment = experiment
        self.job_container_name = job_container_name or constants.JOB_CONTAINER_NAME
        self.job_docker_image = job_docker_image or constants.JOB_DOCKER_NAME
        self.sidecar_container_name = sidecar_container_name or constants.SIDECAR_CONTAINER_NAME
        self.sidecar_docker_image = sidecar_docker_image or constants.SIDECAR_DOCKER_IMAGE
        self.role_label = role_label or constants.ROLE_LABELS_WORKER
        self.type_label = type_label or constants.TYPE_LABELS_EXPERIMENT
        self.ports = ports or [constants.DEFAULT_PORT]
        self.use_sidecar = use_sidecar
        if use_sidecar and not sidecar_config:
            raise PolyaxonConfigurationError(
                'In order to use a `sidecar_config` is required. '
                'The `sidecar_config` must correspond to the sidecar docker image used.')
        self.sidecar_config = sidecar_config

    def get_task_name(self, task_type, task_idx):
        return constants.TASK_NAME.format(project=self.project,
                                          experiment=self.experiment,
                                          task_type=task_type,
                                          task_idx=task_idx)

    def get_task_id(self, task_name):
        return uuid.uuid5(uuid.NAMESPACE_DNS, task_name).hex

    def set_experiment(self, experiment):
        self.experiment = experiment

    def get_cluster_env_var(self, task_type):
        name = constants.CONFIG_MAP_NAME.format(project=self.project,
                                                experiment=self.experiment,
                                                role='cluster')
        config_map_key_ref = client.V1ConfigMapKeySelector(name=name, key=task_type)
        value = client.V1EnvVarSource(config_map_key_ref=config_map_key_ref)
        key_name = constants.CONFIG_MAP_KEY_NAME.format(project=self.project.replace('-', '_'),
                                                        experiment=self.experiment,
                                                        role='cluster',
                                                        task_type=task_type)
        return client.V1EnvVar(name=key_name, value_from=value)

    def get_pod_container(self,
                          volume_mounts,
                          env_vars=None,
                          command=None,
                          args=None,
                          resources=None):
        """Pod job container for task."""
        env_vars = env_vars or []
        env_vars += [
            self.get_cluster_env_var(task_type=TaskType.MASTER),
            self.get_cluster_env_var(task_type=TaskType.WORKER),
            self.get_cluster_env_var(task_type=TaskType.PS),
        ]

        ports = [client.V1ContainerPort(container_port=port) for port in self.ports]
        return client.V1Container(name=self.job_container_name,
                                  image=self.job_docker_image,
                                  command=command,
                                  args=args,
                                  ports=ports,
                                  env=env_vars,
                                  resources=get_resources(resources),
                                  volume_mounts=volume_mounts)

    def get_sidecar_container(self, task_type, task_idx, args, resources=None):
        """Pod sidecar container for task logs."""
        task_name = self.get_task_name(task_type=task_type, task_idx=task_idx)

        env_vars = [
            client.V1EnvVar(name='POLYAXON_K8S_NAMESPACE', value=self.namespace),
            client.V1EnvVar(name='POLYAXON_POD_ID', value=task_name),
            client.V1EnvVar(name='POLYAXON_JOB_ID', value=self.job_container_name),
        ]
        for k, v in six.iteritems(self.sidecar_config):
            env_vars.append(client.V1EnvVar(name=k, value=v))
        return client.V1Container(name=self.sidecar_container_name,
                                  image=self.sidecar_docker_image,
                                  env=env_vars,
                                  args=args,
                                  resources=resources)

    def get_task_pod_spec(self,
                          task_type,
                          task_idx,
                          volume_mounts,
                          volumes,
                          env_vars=None,
                          command=None,
                          args=None,
                          sidecar_args=None,
                          resources=None,
                          restart_policy='OnFailure'):
        """Pod spec to be used to create pods for tasks: master, worker, ps."""
        volume_mounts = volume_mounts or []
        volumes = volumes or []

        if resources and resources.gpu:
            volume_mounts += get_gpu_volume_mounts()
            volumes += get_gpu_volumes()

        pod_container = self.get_pod_container(volume_mounts=volume_mounts,
                                               env_vars=env_vars,
                                               command=command,
                                               args=args,
                                               resources=resources)

        containers = [pod_container]
        if self.use_sidecar:
            sidecar_container = self.get_sidecar_container(task_type=task_type,
                                                           task_idx=task_idx,
                                                           args=sidecar_args,
                                                           resources=resources)
            containers.append(sidecar_container)
        return client.V1PodSpec(restart_policy=restart_policy,
                                containers=containers,
                                volumes=volumes)

    def get_labels(self, task_type, task_idx, task_name):
        return {'project': self.project,
                'experiment': '{}'.format(self.experiment),
                'task_type': task_type,
                'task_idx': '{}'.format(task_idx),
                'task': task_name,
                'task_id': self.get_task_id(task_name),
                'role': self.role_label,
                'type': self.type_label}

    def get_pod(self,
                task_type,
                task_idx,
                volume_mounts,
                volumes,
                command=None,
                args=None,
                sidecar_args=None,
                resources=None,
                restart_policy=None):
        task_name = self.get_task_name(task_type=task_type, task_idx=task_idx)
        labels = self.get_labels(task_type=task_type,
                                 task_idx=task_idx,
                                 task_name=task_name)
        metadata = client.V1ObjectMeta(name=task_name, labels=labels, namespace=self.namespace)

        pod_spec = self.get_task_pod_spec(
            task_type=task_type,
            task_idx=task_idx,
            volume_mounts=volume_mounts,
            volumes=volumes,
            command=command,
            args=args,
            sidecar_args=sidecar_args,
            resources=resources,
            restart_policy=restart_policy)
        return client.V1Pod(api_version=k8s_constants.K8S_API_VERSION_V1,
                            kind=k8s_constants.K8S_POD_KIND,
                            metadata=metadata,
                            spec=pod_spec)
