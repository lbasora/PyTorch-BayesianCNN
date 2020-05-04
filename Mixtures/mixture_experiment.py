import sys
sys.path.append('..')

import os
import datetime
import torch
import contextlib

from utils_mixture import *
# from layers.BBBLinear import BBBLinear


@contextlib.contextmanager
def print_to_logfile(file):
    # capture all outputs to a log file while still printing it
    class Logger:
        def __init__(self, file):
            self.terminal = sys.stdout
            self.log = file

        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)

        def __getattr__(self, attr):
            return getattr(self.terminal, attr)

    logger = Logger(file)

    _stdout = sys.stdout
    sys.stdout = logger
    try:
        yield logger.log
    finally:
        sys.stdout = _stdout


def initiate_experiment(experiment):

    def decorator(*args, **kwargs):
        log_file_dir = "experiments/mixtures/"
        log_file = log_file_dir + experiment.__name__ + ".txt"
        if not os.path.exists(log_file):
            os.makedirs(log_file_dir, exist_ok=True)
        with print_to_logfile(open(log_file, 'a')):
            print("Performing experiment:", experiment.__name__)
            print("Date-Time:", datetime.datetime.now())
            print("\n", end="")
            print("Args:", args)
            print("Kwargs:", kwargs)
            print("\n", end="")
            experiment(*args, **kwargs)
            print("\n\n", end="")
    return decorator


@initiate_experiment
def experiment_regular_prediction_bayesian(num_tasks, net_type='lenet', layer_type='lrt', activation_type='softplus', num_ens=25, comment=None):

    weights_dir = "checkpoints/MNIST/bayesian/splitted/{}-tasks/".format(num_tasks)

    loaders = get_splitmnist_dataloaders(num_tasks)
    nets = get_splitmnist_models(num_tasks, True, True, weights_dir, net_type, layer_type, activation_type)

    for i in range(num_tasks):
        net = nets[i]
        net.cuda()
        loader = loaders[i][1]  # valid_loader
        print("Model-{}, Task-{}-Dataset=> Accuracy: {:.3}".format(i + 1, i + 1, predict_regular(net, loader, True, num_ens)))


@initiate_experiment
def experiment_regular_prediction_frequentist(num_tasks, net_type='lenet', comment=None):
    weights_dir = "checkpoints/MNIST/frequentist/splitted/{}-tasks/".format(num_tasks)

    loaders = get_splitmnist_dataloaders(num_tasks)
    nets = get_splitmnist_models(num_tasks, False, True, weights_dir, net_type)

    for i in range(num_tasks):
        net = nets[i]
        net.cuda()
        loader = loaders[i][1]  # valid_loader
        print("Model-{}, Task-{}-Dataset=> Accuracy: {:.3}".format(i + 1, i + 1, predict_regular(net, loader, False)))


@initiate_experiment
def experiment_multi_model_with_uncertainty(num_tasks, net_type='lenet', layer_type='lrt', activation_type='softplus',
                                                                   uncertainty_type="epistemic_softmax", T=25, weights_dir=None, comment=None):

    weights_dir = "checkpoints/MNIST/bayesian/splitted/{}-tasks/".format(num_tasks)

    loaders = get_splitmnist_dataloaders(num_tasks)
    nets = get_splitmnist_models(num_tasks, True, True, weights_dir, net_type, layer_type, activation_type)

    for i in range(num_tasks):
        loader = loaders[i][1]  # valid_loader
        acc, model_selected, model_uncertainties = \
            predict_using_uncertainty_multi_model(nets, loader, uncertainty_type=uncertainty_type, T=T)

        print("All Models, Task-{}-Dataset=> Accuracy: {:.3}".format(i + 1, acc))
        for j in range(num_tasks):
            print("Model-{}-Preferred: {:.3}\tModel-{}-Uncertainty: {:.3}".format(
                j + 1, model_selected[j], j + 1, model_uncertainties[j]))
        print("\n", end="")


@initiate_experiment
def experiment_multi_model_with_confidence(num_tasks, net_type='lenet', comment=None):
    weights_dir = "checkpoints/MNIST/frequentist/splitted/{}-tasks/".format(num_tasks)

    loaders = get_splitmnist_dataloaders(num_tasks)
    nets = get_splitmnist_models(num_tasks, False, True, weights_dir, net_type)

    for i in range(num_tasks):
        loader = loaders[i][1]  # valid_loader
        acc, model_selected = predict_using_confidence_multi_model(nets, loader)

        print("All Models, Task-{}-Dataset=> Accuracy: {:.3}".format(i + 1, acc))
        for j in range(num_tasks):
            print("Model-{}-selected: {:.3}".format(j + 1, model_selected[j]))
        print("\n", end="")


@initiate_experiment
def wip_experiment_average_weights_mixture_model():
    num_tasks = 2
    weights_dir = "checkpoints/MNIST/bayesian/splitted/2-tasks/"

    loaders1, loaders2 = get_splitmnist_dataloaders(num_tasks)
    net1, net2 = get_splitmnist_models(num_tasks, True, weights_dir)
    net1.cuda()
    net2.cuda()
    net_mix = get_mixture_model(num_tasks, weights_dir, include_last_layer=True)
    net_mix.cuda()

    print("Model-1, Loader-1:", calculate_accuracy(net1, loaders1[1]))
    print("Model-2, Loader-2:", calculate_accuracy(net2, loaders2[1]))
    print("Model-1, Loader-2:", calculate_accuracy(net1, loaders2[1]))
    print("Model-2, Loader-1:", calculate_accuracy(net2, loaders1[1]))
    print("Model-Mix, Loader-1:", calculate_accuracy(net_mix, loaders1[1]))
    print("Model-Mix, Loader-2:", calculate_accuracy(net_mix, loaders2[1]))


@initiate_experiment
def wip_experiment_simultaneous_average_weights_mixture_model_with_uncertainty():
    num_tasks = 2
    weights_dir = "checkpoints/MNIST/bayesian/splitted/2-tasks/"

    loaders1, loaders2 = get_splitmnist_dataloaders(num_tasks)
    net1, net2 = get_splitmnist_models(num_tasks, True, weights_dir)
    net1.cuda()
    net2.cuda()
    net_mix = get_mixture_model(num_tasks, weights_dir, include_last_layer=False)
    net_mix.cuda()

    # Creating 2 sets of last layer
    fc3_1 = BBBLinear(84, 5, name='fc3_1') # hardcoded for lenet
    weights_1 = torch.load(weights_dir + "model_lenet_2.1.pt")
    fc3_1.W = torch.nn.Parameter(weights_1['fc3.W'])
    fc3_1.log_alpha = torch.nn.Parameter(weights_1['fc3.log_alpha'])

    fc3_2 = BBBLinear(84, 5, name='fc3_2') # hardcoded for lenet
    weights_2 = torch.load(weights_dir + "model_lenet_2.2.pt")
    fc3_2.W = torch.nn.Parameter(weights_2['fc3.W'])
    fc3_2.log_alpha = torch.nn.Parameter(weights_2['fc3.log_alpha'])

    fc3_1, fc3_2 = fc3_1.cuda(), fc3_2.cuda()

    print("Model-1, Loader-1:", calculate_accuracy(net1, loaders1[1]))
    print("Model-2, Loader-2:", calculate_accuracy(net2, loaders2[1]))
    print("Model-Mix, Loader-1:", predict_using_epistemic_uncertainty_with_mixture_model(net_mix, fc3_1, fc3_2, loaders1[1]))
    print("Model-Mix, Loader-2:", predict_using_epistemic_uncertainty_with_mixture_model(net_mix, fc3_1, fc3_2, loaders2[1]))


if __name__ == '__main__':
    experiment_multi_model_with_uncertainty(2)