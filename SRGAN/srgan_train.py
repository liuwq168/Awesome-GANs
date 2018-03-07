from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import srgan_model as srgan

sys.path.append('../')
import image_utils as iu
from datasets import Div2KDataSet as DataSet


results = {
    'output': './gen_img/',
    'checkpoint': './model/checkpoint',
    'model': './model/SRGAN-model.ckpt'
}

train_step = {
    'global_step': 300001,
    'logging_interval': 2500,
}


def resize(s, x):
    x = tf.convert_to_tensor(x, dtype=tf.float32)  # ndarray to tensor

    x_small = tf.image.resize_images(x, [96, 96],
                                     tf.image.ResizeMethod.BICUBIC)  # LR image
    x_nearest = tf.image.resize_images(x_small, [384, 384],
                                       tf.image.ResizeMethod.NEAREST_NEIGHBOR)  # HR image

    x_small = s.run(x_small)      # tensor to ndarray
    x_nearest = s.run(x_nearest)  # tensor to ndarray

    return x_small, x_nearest


def main():
    start_time = time.time()  # Clocking start

    # Div2K -  Track 1: Bicubic downscaling - x4 DataSet load
    hr_lr_images = DataSet().images
    hr, lr = hr_lr_images[0],  hr_lr_images[1]

    # GPU configure
    gpu_config = tf.GPUOptions(allow_growth=True)
    config = tf.ConfigProto(allow_soft_placement=True, gpu_options=gpu_config)

    with tf.Session(config=config) as s:
        # SRGAN Model
        model = srgan.SRGAN(s)

        # Initializing
        s.run(tf.global_variables_initializer())

        sample_x, _ = mnist.train.next_batch(model.sample_num)
        sample_x = np.reshape(sample_x, [-1] + model.hr_image_shape[1:])
        sample_x_small, sample_x_nearest = resize(s, sample_x)

        for step in range(train_step['global_step']):
            batch_x, _ = mnist.train.next_batch(model.batch_size)
            batch_x = np.reshape(batch_x, [-1] + model.hr_image_shape[1:])
            batch_x_small, batch_x_nearest = resize(s, batch_x)

            # Update D network
            _, d_loss = s.run([model.d_op, model.d_loss],
                              feed_dict={
                                  model.x_lr: batch_x_small,
                                  model.x_hr: batch_x_nearest,
                              })

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.x_lr: batch_x_small,
                              })

            if step % train_step['logging_interval'] == 0:
                batch_x, _ = mnist.train.next_batch(model.batch_size)
                batch_x = np.reshape(batch_x, [-1] + model.hr_image_shape[1:])
                batch_x_small, batch_x_nearest = resize(s, batch_x)

                d_loss, g_loss, summary = s.run([model.d_loss, model.g_loss, model.merged],
                                                feed_dict={
                                                    model.x_lr: batch_x_small,
                                                    model.x_hr: batch_x_nearest,
                                                })
                # Print loss
                print("[+] Step %08d => " % step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                samples = s.run(model.g,
                                feed_dict={
                                    model.x_lr: sample_x_small,
                                })

                samples = np.reshape(samples, [-1] + model.hr_image_shape[1:])

                # Summary saver
                model.writer.add_summary(summary, step)

                # Export image generated by model G
                sample_image_height = model.output_height
                sample_image_width = model.output_width
                sample_dir = results['output'] + 'train_{:08d}.png'.format(step)

                # Generated image save
                iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir)

                # Model save
                model.saver.save(s, results['model'], global_step=step)

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
