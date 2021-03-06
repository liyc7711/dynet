import dynet as dy
import numpy as np
import unittest


class TestInput(unittest.TestCase):

    def setUp(self):
        self.input_vals = np.arange(81)
        self.squared_norm = (self.input_vals**2).sum()
        self.shapes = [(81,), (3, 27), (3, 3, 9), (3, 3, 3, 3)]

    def test_inputTensor_not_batched(self):
        for i in range(4):
            dy.renew_cg()
            input_tensor = self.input_vals.reshape(self.shapes[i])
            x = dy.inputTensor(input_tensor)
            self.assertEqual(x.dim()[0], self.shapes[i],
                             msg="Dimension mismatch")
            self.assertEqual(x.dim()[1], 1,
                             msg="Dimension mismatch")
            self.assertTrue(np.allclose(x.npvalue(), input_tensor),
                            msg="Expression value different from initial value")
            self.assertEqual(dy.squared_norm(x).scalar_value(), self.squared_norm,
                             msg="Value mismatch")

    def test_inputTensor_batched(self):
        for i in range(4):
            dy.renew_cg()
            input_tensor = self.input_vals.reshape(self.shapes[i])
            xb = dy.inputTensor(input_tensor, batched=True)
            self.assertEqual(xb.dim()[0], (self.shapes[i][:-1] if i > 0 else (1,)),
                             msg="Dimension mismatch")
            self.assertEqual(xb.dim()[1], self.shapes[i][-1],
                             msg="Dimension mismatch")
            self.assertTrue(np.allclose(xb.npvalue(), input_tensor),
                            msg="Expression value different from initial value")
            self.assertEqual(dy.sum_batches(dy.squared_norm(xb)).scalar_value(),
                             self.squared_norm, msg="Value mismatch")

    def test_inputTensor_batched_list(self):
        for i in range(4):
            dy.renew_cg()
            input_tensor = self.input_vals.reshape(self.shapes[i])
            xb = dy.inputTensor([np.asarray(x).transpose() for x in input_tensor.transpose()])
            self.assertEqual(xb.dim()[0], (self.shapes[i][:-1] if i > 0 else (1,)),
                             msg="Dimension mismatch")
            self.assertEqual(xb.dim()[1], self.shapes[i][-1],
                             msg="Dimension mismatch")
            self.assertTrue(np.allclose(xb.npvalue(), input_tensor),
                            msg="Expression value different from initial value")
            self.assertEqual(dy.sum_batches(dy.squared_norm(xb)).scalar_value(),
                             self.squared_norm, msg="Value mismatch")

    def test_inputTensor_except(self):
        dy.renew_cg()
        self.assertRaises(TypeError, dy.inputTensor, batched=True)


class TestParameters(unittest.TestCase):

    def setUp(self):
        # Create model
        self.m = dy.Model()
        # Parameters
        self.p1 = self.m.add_parameters((10, 10), init=dy.ConstInitializer(1))
        self.p2 = self.m.add_parameters((10, 10), init=dy.ConstInitializer(1))
        self.lp1 = self.m.add_lookup_parameters((10, 10), init=dy.ConstInitializer(1))
        self.lp2 = self.m.add_lookup_parameters((10, 10), init=dy.ConstInitializer(1))
        # Trainer
        self.trainer = dy.SimpleSGDTrainer(self.m,e0=0.1)
        self.trainer.set_clip_threshold(-1)

    def test_grad(self):
        # add parameter
        p = self.m.parameters_from_numpy(np.arange(5))
        # create cg
        dy.renew_cg()
        # input tensor
        x = dy.inputTensor(np.arange(5).reshape((1, 5)))
        # add parameter to computation graph
        e_p = dy.parameter(p)
        # compute dot product
        res = x * e_p
        # Run forward and backward pass
        res.forward()
        res.backward()
        # Should print the value of x
        self.assertTrue(np.allclose(p.grad_as_array(), x.npvalue()), msg="Gradient is wrong")

    def test_is_updated(self):
        self.assertTrue(self.p1.is_updated())
        self.assertTrue(self.p2.is_updated())
        self.assertTrue(self.lp1.is_updated())
        self.assertTrue(self.lp2.is_updated())

    def test_set_updated(self):
        self.p2.set_updated(False)
        self.lp1.set_updated(False)

        self.assertTrue(self.p1.is_updated())
        self.assertFalse(self.p2.is_updated())
        self.assertFalse(self.lp1.is_updated())
        self.assertTrue(self.lp2.is_updated())

        self.p1.set_updated(True)
        self.p2.set_updated(False)
        self.lp1.set_updated(False)
        self.lp2.set_updated(True)

        self.assertTrue(self.p1.is_updated())
        self.assertFalse(self.p2.is_updated())
        self.assertFalse(self.lp1.is_updated())
        self.assertTrue(self.lp2.is_updated())

        self.p1.set_updated(False)
        self.p2.set_updated(True)
        self.lp1.set_updated(True)
        self.lp2.set_updated(False)

        self.assertFalse(self.p1.is_updated())
        self.assertTrue(self.p2.is_updated())
        self.assertTrue(self.lp1.is_updated())
        self.assertFalse(self.lp2.is_updated())

    def test_update(self):
        ones=np.ones((10, 10))
        updated = np.ones((10, 10)) * 0.99
        gradient = np.ones((10, 10)) * 0.01

        dy.renew_cg()
        pp1 = dy.parameter(self.p1)
        pp2 = dy.parameter(self.p2)

        a = pp1 * self.lp1[1]
        b = pp2 * self.lp2[1]
        l = dy.dot_product(a, b) / 100
        self.assertEqual(l.scalar_value(),10,msg=str(l.scalar_value()))
        l.backward()

        self.assertTrue(np.allclose(self.p1.grad_as_array(), 0.1 * ones),msg=np.array_str(self.p1.grad_as_array()))
        self.assertTrue(np.allclose(self.p2.grad_as_array(), 0.1 * ones),msg=np.array_str(self.p2.grad_as_array()))
        self.assertTrue(np.allclose(self.lp1.grad_as_array()[1], ones[0]),msg=np.array_str(self.lp1.grad_as_array()))
        self.assertTrue(np.allclose(self.lp2.grad_as_array()[1], ones[0]),msg=np.array_str(self.lp2.grad_as_array()))

        self.trainer.update()



        self.assertTrue(np.allclose(self.p1.as_array(), ones * 0.99),msg=np.array_str(self.p1.as_array()))
        self.assertTrue(np.allclose(self.p2.as_array(), ones * 0.99),msg=np.array_str(self.p2.as_array()))
        self.assertTrue(np.allclose(self.lp1.as_array()[1], ones[0] * 0.9),msg=np.array_str(self.lp1.as_array()[1]))
        self.assertTrue(np.allclose(self.lp2.as_array()[1], ones[0] * 0.9),msg=np.array_str(self.lp2.as_array()))



class TestBatchManipulation(unittest.TestCase):

    def setUp(self):
        # create model
        self.m = dy.Model()
        # Parameter
        self.p = self.m.add_lookup_parameters((2, 3))
        # Values
        self.pval = np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        self.p.init_from_array(self.pval)

    def test_lookup_batch(self):
        dy.renew_cg()
        x = dy.lookup_batch(self.p, [0, 1])
        self.assertTrue(np.allclose(x.npvalue(), self.pval.T))

    def test_pick_batch_elem(self):
        dy.renew_cg()
        x = dy.lookup_batch(self.p, [0, 1])
        y = dy.pick_batch_elem(x, 1)
        self.assertTrue(np.allclose(y.npvalue(), self.pval[1]))

    def test_pick_batch_elems(self):
        dy.renew_cg()
        x = dy.lookup_batch(self.p, [0, 1])
        y = dy.pick_batch_elems(x, [0])
        self.assertTrue(np.allclose(y.npvalue(), self.pval[0]))
        z = dy.pick_batch_elems(x, [0, 1])
        self.assertTrue(np.allclose(z.npvalue(), self.pval.T))

    def test_concat_to_batch(self):
        dy.renew_cg()
        x = dy.lookup_batch(self.p, [0, 1])
        y = dy.pick_batch_elem(x, 0)
        z = dy.pick_batch_elem(x, 1)
        w = dy.concat_to_batch([y, z])
        self.assertTrue(np.allclose(w.npvalue(), self.pval.T))


class TestIO(unittest.TestCase):

    def setUp(self):
        self.file = "bilstm.model"
        # create models
        self.m = dy.Model()
        self.m2 = dy.Model()
        # Create birnn
        self.b = dy.BiRNNBuilder(2, 10, 10, self.m, dy.LSTMBuilder)

    def test_save_load(self):
        self.m.save(self.file, [self.b])
        self.m2.load(self.file)


if __name__ == '__main__':
    unittest.main()
