# Neural Networks

Neural networks learn useful representations from examples. A network is composed of layers,
and each layer transforms an input into a new representation.

## Neurons and weights

A neuron combines input values using trainable weights and a bias. An activation function then
introduces non-linearity, allowing the network to model complex relationships.

## Forward propagation

During forward propagation, data moves from the input layer through hidden layers to the output.
The output is compared with the expected result using a loss function.

## Backpropagation

Backpropagation calculates gradients of the loss with respect to each weight. Gradient descent
uses these gradients to update the parameters and reduce future prediction error.

## Training and validation

Training data updates the model parameters. Validation data measures generalization and helps
detect overfitting before the model is evaluated on unseen test data.
