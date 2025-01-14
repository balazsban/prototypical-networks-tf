import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.layers import Dense, Flatten, Conv2D
from tensorflow.keras import Model
from tensorflow.keras.models import load_model


def calc_euclidian_dists(x, y):
    """
    Calculate euclidian distance between two 3D tensors.

    Args:
        x (tf.Tensor):
        y (tf.Tensor):

    Returns (tf.Tensor): 2-dim tensor with distances.

    """
    n = x.shape[0]
    m = y.shape[0]
    x = tf.tile(tf.expand_dims(x, 1), [1, m, 1])
    y = tf.tile(tf.expand_dims(y, 0), [n, 1, 1])
    return tf.reduce_mean(tf.math.pow(x - y, 2), 2)


class Prototypical(Model):
    """
    Implemenation of Prototypical Network.
    """
    def __init__(self, n_support, n_query, w, h, c):
        """
        Args:
            n_support (int): number of support examples.
            n_query (int): number of query examples.
            w (int): image width .
            h (int): image height.
            c (int): number of channels.
        """
        super(Prototypical, self).__init__()
        self.w, self.h, self.c = w, h, c

        self.conv_layers = [
            tf.keras.layers.Conv2D(filters=64, kernel_size=3, padding="same", activation='relu'),
            tf.keras.layers.Conv2D(filters=64, kernel_size=3, padding="same", activation='relu'),
            tf.keras.layers.Conv2D(filters=64, kernel_size=3, padding="same", activation='relu'),
            tf.keras.layers.Conv2D(filters=64, kernel_size=3, padding="same", activation='relu')
        ]
        self.max_pool_layers = [
            tf.keras.layers.MaxPool2D(),
            tf.keras.layers.MaxPool2D(),
            tf.keras.layers.MaxPool2D(),
            tf.keras.layers.MaxPool2D()
        ]
        self.batch_norm_layers = [
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.BatchNormalization()
        ]
        self.flatten_layer = tf.keras.layers.Flatten()

    def call(self, support, query, training=False):
        n_class = support.shape[0]
        n_support = support.shape[1]
        n_query = query.shape[1]
        y = np.tile(np.arange(n_class)[:, np.newaxis], (1, n_query))
        y_onehot = tf.cast(tf.one_hot(y, n_class), tf.float32)

        # correct indices of support samples (just natural order)
        target_inds = tf.reshape(tf.range(n_class), [n_class, 1])
        target_inds = tf.tile(target_inds, [1, n_query])

        x = tf.reshape(support, [n_class * n_support, self.w, self.h, self.c])

        for i in range(len(self.conv_layers)):
            x = self.conv_layers[i](x)
            x = self.max_pool_layers[i](x)
            x = self.batch_norm_layers[i](x, training=True)
        z_support = self.flatten_layer(x)

        z_prototypes = tf.reshape(z_support, [n_class, n_support, z_support.shape[-1]])
        z_prototypes = tf.math.reduce_mean(z_prototypes, axis=1)

        x = tf.reshape(query, [n_class * n_query, self.w, self.h, self.c])

        for i in range(len(self.conv_layers)):
            x = self.conv_layers[i](x)
            x = self.max_pool_layers[i](x)
            x = self.batch_norm_layers[i](x, training=False)
        z_query = self.flatten_layer(x)

        # Calculate distances between query and prototypes
        dists = calc_euclidian_dists(z_query, z_prototypes)

        # log softmax of calculated distances
        log_p_y = tf.nn.log_softmax(-dists, axis=-1)
        log_p_y = tf.reshape(log_p_y, [n_class, n_query, -1])
        
        loss = -tf.reduce_mean(tf.reshape(tf.reduce_sum(tf.multiply(y_onehot, log_p_y), axis=-1), [-1]))
        eq = tf.cast(tf.equal(
            tf.cast(tf.argmax(log_p_y, axis=-1), tf.int32), 
            tf.cast(y, tf.int32)), tf.float32)
        acc = tf.reduce_mean(eq)
        return loss, acc

    def save(self, model_path):
        """
        Save encoder to the file.

        Args:
            model_path (str): path to the .h5 file.

        Returns: None

        """
        self.save(model_path)

    def load(self, model_path):
        """
        Load encoder from the file.

        Args:
            model_path (str): path to the .h5 file.

        Returns: None

        """
        # self.encoder(tf.zeros([1, self.w, self.h, self.c]))
        self.load_weights(model_path)
