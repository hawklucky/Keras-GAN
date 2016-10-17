import numpy as np

from keras.layers import Dense, Activation, Reshape, Flatten, Input, Lambda
from keras.layers.advanced_activations import LeakyReLU
from keras.layers.convolutional import Convolution2D, ZeroPadding2D
from keras.layers.normalization import BatchNormalization
from keras.models import Sequential, Model
import keras
import keras.backend as K

from ..layers import Deconvolution2D, BN # does not converge when using the default BN layer
from ..utils.init import InitNormal
from ..utils.dist import ProductDist

class Generator(Sequential):
    def __init__(self, 
                    g_size=(3, 128, 64),
                    g_nb_filters=128,
                    g_nb_coding=200,
                    g_scales=4,
                    g_FC=None,
                **kwargs):
        super(Generator, self).__init__(**kwargs)
        
        self.g_size = g_size
        self.g_nb_filters = g_nb_filters
        self.g_nb_coding = g_nb_coding 
        self.g_scales = g_scales
        self.g_FC = g_FC

        c, h, w = g_size # h and w should be multiply of 16
        nf = g_nb_filters
        if g_FC is None:
            self.add( Dense(nf*(2**(g_scales-1)) * (h/2**g_scales) * (w/2**g_scales), input_shape=(g_nb_coding,), init=InitNormal) )
        else:
            self.add( Dense(g_FC[0], init=InitNormal, input_shape=(g_nb_coding,)) )
            self.add( BN() )
#           self.add( BatchNormalization(beta_init='zero', gamma_init='one', mode=2) )
            self.add( Activation('relu') )
            for fc_dim in g_FC[1:]:
                self.add( Dense(fc_dim, init=InitNormal) )
                self.add( BN() )
#               self.add( BatchNormalization(beta_init='zero', gamma_init='one', mode=2) )
                self.add( Activation('relu') )
            self.add( Dense(nf*(2**(g_scales-1)) * (h/2**g_scales) * (w/2**g_scales), init=InitNormal) )
        self.add( BN() )
#       self.add( BatchNormalization(beta_init='zero', gamma_init='one', axis=1, mode=2) )
        self.add( Activation('relu') )
        self.add( Reshape((nf*(2**(g_scales-1)), h/2**g_scales, w/2**g_scales)) )
#       self.intermediate = [self.layers[-1].output]

        for s in range(g_scales-2, -1, -1):
            self.add( Deconvolution2D(nf*(2**s), 5, 5, subsample=(2,2), border_mode=(2,2), init=InitNormal) )
            self.add( BN() )
#           self.add( BatchNormalization(beta_init='zero', gamma_init='one', axis=1, mode=2) )
            self.add( Activation('relu') )
#           self.intermediate.append(self.layers[-1].output)

        self.add( Deconvolution2D(c, 5, 5, subsample=(2,2), border_mode=(2,2), init=InitNormal) )
        self.add( Activation('tanh') )
#       self.intermediate.append(self.layers[-1].output)
#       self._generate_intermediate = K.function([self.input], self.intermediate) 

    def generate(self, x):
        return self.predict(x) 

    def random_generate(self, batch_size=128):
        return self.predict(np.random.random((batch_size, self.g_nb_coding)) )

    def sample(self, batch_size=128):
        return np.random.uniform(-1, 1, size=(batch_size, self.g_nb_coding))

#   def generate_intermediate(self, x):
#       return self._generate_intermediate([x])



class ConditionalGenerator(Model):
    def __init__(self, 
                    g_size=(3, 128, 64),
                    g_cond_dim=10, 
                    g_nb_filters=128,
                    g_nb_coding=200,
                    g_scales=4,
                    g_FC=None,
                **kwargs): 
        self.g_cond_dim = g_cond_dim
        self.g_size = g_size
        self.g_nb_filters = g_nb_filters
        self.g_nb_coding = g_nb_coding 
        self.g_scales = g_scales
        self.g_FC = g_FC

        c, h, w = g_size 
        nf = g_nb_filters

        raise NotImplemented
        super(ConditionalGenerator, self).__init__(**kwargs)



class InfoGenerator(Generator):
    def __init__(self, 
                    g_nb_noise=200,
                    g_info=[], # list of distributions (GAN/utils/dist.py)
                **kwargs):

        if isinstance(g_info, list):
            self.g_info = ProductDist(g_info) 
        elif isinstance(g_info, ProductDist):
            self.g_info = g_info
        self.g_nb_noise = g_nb_noise
#       self.info_split_layer = Lambda(lambda x: x[:, self.g_nb_noise:], lambda s: (s[0], self.dim))

        super(InfoGenerator, self).\
            __init__(g_nb_coding=g_nb_noise+self.g_info.dim, **kwargs)

    def get_info_coding(self, tensor):
        return tensor[:, self.g_nb_noise:] 
#       return self.info_split_layer(tensor)

    def generate(self, x, info_param):
        raise NotImplemented

    def random_generate(self, batch_size=128):
        raise NotImplemented

    def generate_intermediate(self, x):
        raise NotImplemented

    def sample(self, batch_size=128):
        x = np.concatenate([
            np.random.uniform(-1, 1, size=(batch_size, self.g_nb_noise)),
            self.g_info.sample(batch_size)
        ], axis=1)
        assert x.ndim == 2
        assert x.shape[1] == self.g_nb_coding
        return x
