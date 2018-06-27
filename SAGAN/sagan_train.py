from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import sagan_model as sagan

sys.path.append('../')
import image_utils as iu
from datasets import DataIterator
from datasets import CelebADataSet as DataSet


results = {
    'output': './gen_img/',
    'model': './model/SAGAN-model.ckpt'
}

train_step = {
    'epochs': 101,
    'batch_size': 64,
    'global_step': 100001,
    'logging_interval': 500,
}


def main():
    start_time = time.time()  # Clocking start

    # loading CelebA DataSet
    ds = DataSet(height=64,
                 width=64,
                 channel=3,
                 ds_image_path="D:\\DataSet/CelebA/CelebA-64.h5",
                 ds_label_path="D:\\DataSet/CelebA/Anno/list_attr_celeba.txt",
                 # ds_image_path="D:\\DataSet/CelebA/Img/img_align_celeba/",
                 ds_type="CelebA",
                 use_save=False,
                 save_file_name="D:\\DataSet/CelebA/CelebA-128.h5",
                 save_type="to_h5",
                 use_img_scale=False,
                 # img_scale="-1,1"
                 )

    # saving sample images
    test_images = np.reshape(iu.transform(ds.images[:4], inv_type='127'), (4, 64, 64, 3))
    iu.save_images(test_images,
                   size=[2, 2],
                   image_path=results['output'] + 'sample.png',
                   inv_type='127')

    ds_iter = DataIterator(x=ds.images,
                           y=None,
                           batch_size=train_step['batch_size'],
                           label_off=True)

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # SAGAN Model
        model = sagan.SAGAN(s, batch_size=train_step['batch_size'])

        # Initializing
        s.run(tf.global_variables_initializer())

        sample_y = np.zeros(shape=[model.sample_num, model.n_classes])
        for i in range(10):
            sample_y[10 * i:10 * (i + 1), i] = 1

        global_step = 0
        for epoch in range(train_step['epochs']):
            for batch_x, batch_y in ds_iter.iterate():
                batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                # Update D network
                _, d_loss = s.run([model.d_op, model.d_loss],
                                  feed_dict={
                                      model.x: batch_x,
                                      model.y: batch_y,
                                      model.z: batch_z,
                                  })

                # Update G/C networks
                _, g_loss, _, c_loss = s.run([model.g_op, model.g_loss, model.c_op, model.c_loss],
                                             feed_dict={
                                                 model.x: batch_x,
                                                 model.y: batch_y,
                                                 model.z: batch_z,
                                             })

                if global_step % train_step['logging_interval'] == 0:
                    batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                    d_loss, g_loss, c_loss, summary = s.run([model.d_loss, model.g_loss, model.c_loss, model.merged],
                                                            feed_dict={
                                                                model.x: batch_x,
                                                                model.y: batch_y,
                                                                model.z: batch_z,
                                                            })

                    # Print loss
                    print("[+] Epoch %04d Step %08d => " % (epoch, global_step),
                          " D loss : {:.8f}".format(d_loss),
                          " G loss : {:.8f}".format(g_loss),
                          " C loss : {:.8f}".format(c_loss))

                    # Training G model with sample image and noise
                    sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)
                    samples = s.run(model.g,
                                    feed_dict={
                                        model.y: sample_y,
                                        model.z: sample_z,
                                    })

                    # Summary saver
                    model.writer.add_summary(summary, global_step)

                    # Export image generated by model G
                    sample_image_height = model.sample_size
                    sample_image_width = model.sample_size
                    sample_dir = results['output'] + 'train_{:08d}.png'.format(global_step)

                    # Generated image save
                    iu.save_images(samples,
                                   size=[sample_image_height, sample_image_width],
                                   image_path=sample_dir,
                                   inv_type='127')

                    # Model save
                    model.saver.save(s, results['model'], global_step)

                global_step += 1

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
