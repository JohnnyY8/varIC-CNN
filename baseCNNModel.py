#coding=utf-8

import os
import math
import numpy as np
import tensorflow as tf

from commonModelFunc import *

class BaseCNNModel(CommonModelFunc):

  def __init__(self, FLAGS, insDataPro):
    self.FLAGS = FLAGS
    self.insDataPro = insDataPro

  # Building CNN graph for base model
  def buildBaseCNNModelGraph(self):
    num4Features = self.FLAGS.num4Features
    maxInputChannels = self.FLAGS.num4InputChannels
    num4FirstFC = self.FLAGS.num4FirstFC
    num4SecondFC = self.FLAGS.num4SecondFC

    self.init = tf.global_variables_initializer()
    self.keepProb = tf.placeholder(
        tf.float32,
        name = "keepProb")

    with tf.variable_scope("inputLayer"):
      self.xData = tf.placeholder(
          tf.float32,
          [None, #self.FLAGS.batchSize,
           num4Features,
           num4InputChannels],
          name = "xData")

      self.xInput = tf.reshape(
          self.xData,
          [-1, 1, num4Features, num4InputChannels],
          name = "xInput")

      self.yLabel = tf.placeholder(
          tf.float32,
          [None, 2],
          name = "yLabel")

    # First convolutional layer
    with tf.variable_scope("conv1Layer"):
      name4Weight, name4Bias = "wConv1", "bConv1"
      name4PreAct, name4Act = "preActConv1", "hConv1"

      conv1KHeight = 1
      conv1KWidth = self.FLAGS.conv1KWidth
      conv1SHeight = 1
      conv1SWidth = self.FLAGS.conv1SWidth

      num4OutputChannels = self.FLAGS.num4OutputChannels

      wConv1 = self.init_weight_variable(
          name4Weight,
          [conv1KHeight,
           conv1KWidth,
           num4InputChannels,
           num4OutputChannels])

      bConv1 = self.init_bias_variable(
          name4Bias,
          [num4OutputChannels])

      preActConv1 = tf.add(
          self.conv2d(
              self.xInput,
              wConv1,
              conv1SHeight,
              conv1SWidth),
          bConv1,
          name = name4PreAct)

      hConv1 = tf.nn.relu(preActConv1, name = name4Act)

    # ROI pooling layer
    with tf.variable_scope("roiPoolingLayer"):
      shape4hConv1 = hConv1.get_shape().as_list()
      print "shape4hConv1:", shape4hConv1
      len4AllFM = shape4hConv1[2] * shape4hConv1[3]
      print "len4AllFM:", len4AllFM
      hConv1ForPoolingInput = tf.reshape(
          hConv1,
          [-1, 1, len4AllFM, 1]
          name = "hConv1ForPoolingInput")

      pool1KHeight = 1
      pool1KWidth = int(math.ceil(len4AllFM * 1.0 / num4FirstFC))
      pool1SHeight = 1
      pool1SWidth = int(math.ceil(len4AllFM * 1.0 / num4FirstFC))

      hROIPooling = self.avg_pool(
          hConv1ForPoolingInput,
          pool1KHeight,
          pool1KWidth,
          pool1SHeight,
          pool1SWidth)

      hROIPooling4FCInput = tf.reshape(
          hROIPooling,
          [self.FLAGS.batchSize, -1],  # 这一步的reshape有待验证是否正确
          name = "hROIPooling4FCInput")
      shape4hROIPooling4FCInput = hROIPooling4FCInput.get_shape().as_list()
      print "shape4hROIPooling4FCInput:", shape4hROIPooling4FCInput

    # First fully connected layer
    name4VariableScope = "fc1Layer"
    with tf.variable_scope(name4VariableScope):
      name4Weight, name4Bias = "wFC1", "bFC1"
      name4PreAct, name4Act = "preActFC1", "hFC1"

      wFC1 = self.init_weight_variable(
          name4Weight,
          [shape4hROIPooling4FCInput[1],
           num4FirstFC])
      self.variable_summaries(wFC1)

      bFC1 = self.init_bias_variable(
          name4Bias,
          [num4FirstFC])
      self.variable_summaries(bFC1)

      preActFC1 = tf.add(
          tf.matmul(
              hROIPooling4FCInput,
              wFC1),
          bFC1,
          name = name4PreAct)
      self.variable_summaries(preActFC1)

      hFC1 = tf.nn.relu(
          preActFC1,
          name = name4Act)
      self.variable_summaries(hFC1)

    # Second fully connected layer
    name4VariableScope = "fc2Layer"
    with tf.variable_scope(name4VariableScope):
      name4Weight, name4Bias = "wFC2", "bFC2"
      name4PreAct, name4Act = "preActFC2", "hFC2"

      wFC2 = self.init_weight_variable(
          name4Weight,
          [num4FirstFC, num4SecondFC])
      self.variable_summaries(wFC2)

      bFC2 = self.init_bias_variable(
          name4Bias,
          [num4SecondFC])
      self.variable_summaries(bFC2)

      preActFC2 = tf.add(
          tf.matmul(
              hFC1,
              wFC2),
          bFC2,
          name = name4PreAct)
      self.variable_summaries(preActFC2)

      hFC2 = tf.nn.relu(
          preActFC2,
          name = name4Act)
      self.variable_summaries(hFC2)

      hFC2DropOut = tf.nn.dropout(
          hFC2,
          self.keepProb)
      self.variable_summaries(hFC2DropOut)

    with tf.variable_scope("outputLayer"):
      name4Weight, name4Bias, name4Act = "wOutput", "bOutput", "hOutput"

      wOutput = self.init_weight_variable(name4Weight, [num4SecondFC, 2])
      bOutput = self.init_bias_variable(name4Bias, [2])
      hOutput = tf.matmul(hFC2, wOutput) + bOutput
      print "The shape of hOuput:", hOutput.get_shape().as_list()
      print self.yLabel.shape
      #hOutput = tf.matmul(hFC2DropOut, wOutput) + bOutput
      yOutput = tf.nn.softmax(hOutput, name = name4Act)

    # Cost function
    with tf.variable_scope("costLayer"):
      predPro4PandN = tf.reshape(
          tf.reduce_sum(
              yOutput,
              reduction_indices = [0]),
          [-1, 2])

      predPro4P = tf.matmul(
          predPro4PandN,
          tf.constant([[0.], [1.]]))

      predPro4N = tf.matmul(
          predPro4PandN,
          tf.constant([[1.], [0.]]))

      predPro4PandNwithLabel = tf.reshape(
          tf.reduce_sum(
              self.yLabel * yOutput,
              reduction_indices = [0]),
          [-1, 2])

      predPro4PwithLabel = tf.matmul(
          predPro4PandNwithLabel,
          tf.constant([[0.], [1.]]))

      predPro4NwithLabel = tf.matmul(
          predPro4PandNwithLabel,
          tf.constant([[1.], [0.]]))

      self.cost = tf.subtract(
          tf.reduce_mean(
              tf.nn.softmax_cross_entropy_with_logits(
                  logits = hOutput,
                  labels = self.yLabel)),
          self.FLAGS.nWeight * predPro4NwithLabel,
          name = "loss")
      tf.summary.scalar("lossValue", tf.reduce_mean(self.cost))

      self.trainStep = tf.train.AdamOptimizer(
          self.FLAGS.learningRate).minimize(self.cost)

    # Accuracy
    with tf.variable_scope("accuracyLayer"):
      correctPrediction = tf.equal(tf.argmax(yOutput, 1), tf.argmax(self.yLabel, 1))
      self.accuracy = tf.reduce_mean(tf.cast(correctPrediction, tf.float32))

