"""
This file contains the class Pipeline_ERTS, 
which is used to train and test RTSNet in both linear and non-linear cases.
"""

import torch
import torch.nn as nn
import time
import random
from Plot import Plot_extended as Plot
from Tools.utils import get_mx_0

class Pipeline_ERTS:

    def __init__(self, Time, folderName, modelName,system_config):
        super().__init__()
        self.config = system_config
        self.Time = Time
        self.folderName = folderName + '/'
        self.modelName = modelName
        self.modelFileName = self.folderName + "model_" + self.modelName + ".pt"
        self.PipelineName = self.folderName + "pipeline_" + self.modelName + ".pt"

    def save(self):
        torch.save(self, self.PipelineName)

    def setssModel(self, ssModel):
        self.SysModel = ssModel

    def setModel(self, model):
        self.model = model

    def setTrainingParams(self):
        if self.config.use_cuda:
            self.device = torch.device('cuda')
        else:
            self.device = torch.device('cpu')
        self.num_epochs = self.config.n_epochs  # Number of Training Steps
        self.batch_size = self.config.batch_size # Number of Samples in Batch
        self.learningRate = self.config.lr # Learning Rate
        self.weightDecay = self.config.wd # L2 Weight Regularization - Weight Decay
        # self.alpha = self.config.alpha # Composition loss factor
        # MSE LOSS Function
        self.loss_fn = nn.MSELoss(reduction='mean')

        # Use the optim package to define an Optimizer that will update the weights of
        # the model for us. Here we will use Adam; the optim package contains many other
        # optimization algoriths. The first argument to the Adam constructor tells the
        # optimizer which Tensors it should update.
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learningRate, weight_decay=self.weightDecay)
        # self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, 'min',factor=0.9, patience=20)


    def NNTrain(self, SysModel, train_set, cv_set, path_results, \
        MaskOnState=False, randomInit=False,cv_init=None,train_init=None,\
        train_lengthMask=None,cv_lengthMask=None):

        ### Optional: start training from previous checkpoint
        # model_weights = torch.load(path_results+'best-model-weights.pt', map_location=self.device) 
        # self.model.load_state_dict(model_weights)

        self.train_set_size = len(train_set)
        self.CV_set_size = len(cv_set)

        self.MSE_cv_linear_epoch = torch.zeros([self.num_epochs])
        self.MSE_cv_dB_epoch = torch.zeros([self.num_epochs])

        self.MSE_train_linear_epoch = torch.zeros([self.num_epochs])
        self.MSE_train_dB_epoch = torch.zeros([self.num_epochs])
        
        if MaskOnState:
            mask = torch.tensor([True,False,False])
            if SysModel.space_state_size == 2: 
                mask = torch.tensor([True,False])

        ##############
        ### Epochs ###
        ##############

        self.MSE_cv_dB_opt = 1000
        self.MSE_cv_idx_opt = 0

        for ti in range(0, self.num_epochs):

            ###############################
            ### Training Sequence Batch ###
            ###############################
            self.optimizer.zero_grad()
            # Training Mode
            self.model.train()
            self.model.batch_size = self.batch_size
            # Init Hidden State
            self.model.init_hidden()

            # Randomly select N_B training sequences
            assert self.batch_size <= self.train_set_size # N_B must be smaller than N_E
            n_e = random.sample(range(self.train_set_size), k=self.batch_size)

            train_batch = [train_set[idx] for idx in n_e]
            traj_lengths_in_batch = torch.tensor([traj.traj_length for traj in train_batch])
            max_traj_lenghth_in_batch = torch.max(traj_lengths_in_batch)

            # Init Training Batch tensors
            y_training_batch = torch.zeros([self.batch_size, SysModel.observation_vector_size, max_traj_lenghth_in_batch])
            train_target_batch = torch.zeros([self.batch_size, SysModel.space_state_size, max_traj_lenghth_in_batch])
            x_out_training_forward_batch = torch.zeros([self.batch_size, SysModel.space_state_size, max_traj_lenghth_in_batch])
            x_out_training_batch = torch.zeros([self.batch_size, SysModel.space_state_size, max_traj_lenghth_in_batch])
            if self.config.randomLength:
                MSE_train_linear_LOSS = torch.zeros([self.batch_size])
                MSE_cv_linear_LOSS = torch.zeros([self.CV_set_size])


            for ii in range(self.batch_size):
                if self.config.randomLength:
                    y_training_batch[ii,:,train_lengthMask[index,:]] = train_set[index,:,train_lengthMask[index,:]].y
                    train_target_batch[ii,:,train_lengthMask[index,:]] = train_set[index,:,train_lengthMask[index,:]].x_real
                else:
                    y_training_batch[ii,:,:traj_lengths_in_batch[ii]] = train_batch[ii].y
                    train_target_batch[ii,:,:traj_lengths_in_batch[ii]] = train_batch[ii].x_real
                ii += 1
            
            M1_0 = []
            for id_in_batch,obs_traj in enumerate(y_training_batch):
                m1_0 = get_mx_0(obs_traj[:,:traj_lengths_in_batch[id_in_batch]]).unsqueeze(0)
                M1_0.append(m1_0)
            M1_0 = torch.cat(M1_0,dim=0).unsqueeze(-1)
            self.model.InitSequence(M1_0,max_traj_lenghth_in_batch)

            # # Init Sequence
            # if(randomInit):
            #     train_init_batch = torch.empty([self.batch_size, SysModel.space_state_size,1])
            #     ii = 0
            #     for index in n_e:
            #         train_init_batch[ii,:,0] = torch.squeeze(train_init[index])
            #         ii += 1
            #     self.model.InitSequence(train_init_batch, SysModel.T)
            # else:
            #     self.model.InitSequence(\
            #     train_set[0].x_real[:,0].reshape(1,SysModel.space_state_size,1).repeat(self.batch_size,1,1), 68)

            
            
            
            # Forward Computation
            for t in range(0,max_traj_lenghth_in_batch):
                x_out_training_forward_batch[:, :, t] = torch.squeeze(self.model(torch.unsqueeze(y_training_batch[:, :, t],2), None, None, None))
            x_out_training_batch[:, :, SysModel.T-1] = x_out_training_forward_batch[:, :, SysModel.T-1] # backward smoothing starts from x_T|T 
            self.model.InitBackward(torch.unsqueeze(x_out_training_batch[:, :, SysModel.T-1],2)) 
            x_out_training_batch[:, :, SysModel.T-2] = torch.squeeze(self.model(None, torch.unsqueeze(x_out_training_forward_batch[:, :, SysModel.T-2],2), torch.unsqueeze(x_out_training_forward_batch[:, :, SysModel.T-1],2),None))
            for t in range(SysModel.T-3, -1, -1):
                x_out_training_batch[:, :, t] = torch.squeeze(self.model(None, torch.unsqueeze(x_out_training_forward_batch[:, :, t],2), torch.unsqueeze(x_out_training_forward_batch[:, :, t+1],2),torch.unsqueeze(x_out_training_batch[:, :, t+2],2)))
                
            # Compute Training Loss
            MSE_trainbatch_linear_LOSS = 0
            if (self.args.CompositionLoss):
                y_hat = torch.zeros([self.batch_size, SysModel.observation_vector_size, SysModel.T])
                for t in range(SysModel.T):
                    y_hat[:,:,t] = torch.squeeze(SysModel.h(torch.unsqueeze(x_out_training_batch[:,:,t],2)))

                if(MaskOnState):### FIXME: composition loss, y_hat may have different mask with x
                    if self.args.randomLength:
                        jj = 0
                        for index in n_e:# mask out the padded part when computing loss
                            MSE_train_linear_LOSS[jj] = self.alpha * self.loss_fn(x_out_training_batch[jj,mask,train_lengthMask[index]], train_target_batch[jj,mask,train_lengthMask[index]])+(1-self.alpha)*self.loss_fn(y_hat[jj,mask,train_lengthMask[index]], y_training_batch[jj,mask,train_lengthMask[index]])
                            jj += 1
                        MSE_trainbatch_linear_LOSS = torch.mean(MSE_train_linear_LOSS)
                    else:                     
                        MSE_trainbatch_linear_LOSS = self.alpha * self.loss_fn(x_out_training_batch[:,mask,:], train_target_batch[:,mask,:])+(1-self.alpha)*self.loss_fn(y_hat[:,mask,:], y_training_batch[:,mask,:])
                else:# no mask on state
                    if self.args.randomLength:
                        jj = 0
                        for index in n_e:# mask out the padded part when computing loss
                            MSE_train_linear_LOSS[jj] = self.alpha * self.loss_fn(x_out_training_batch[jj,:,train_lengthMask[index]], train_target_batch[jj,:,train_lengthMask[index]])+(1-self.alpha)*self.loss_fn(y_hat[jj,:,train_lengthMask[index]], y_training_batch[jj,:,train_lengthMask[index]])
                            jj += 1
                        MSE_trainbatch_linear_LOSS = torch.mean(MSE_train_linear_LOSS)
                    else:                
                        MSE_trainbatch_linear_LOSS = self.alpha * self.loss_fn(x_out_training_batch, train_target_batch)+(1-self.alpha)*self.loss_fn(y_hat, y_training_batch)
            
            else:# no composition loss
                if(MaskOnState):
                    if self.args.randomLength:
                        jj = 0
                        for index in n_e:# mask out the padded part when computing loss
                            MSE_train_linear_LOSS[jj] = self.loss_fn(x_out_training_batch[jj,mask,train_lengthMask[index]], train_target_batch[jj,mask,train_lengthMask[index]])
                            jj += 1
                        MSE_trainbatch_linear_LOSS = torch.mean(MSE_train_linear_LOSS)
                    else:
                        MSE_trainbatch_linear_LOSS = self.loss_fn(x_out_training_batch[:,mask,:], train_target_batch[:,mask,:])
                else: # no mask on state
                    if self.args.randomLength:
                        jj = 0
                        for index in n_e:# mask out the padded part when computing loss
                            MSE_train_linear_LOSS[jj] = self.loss_fn(x_out_training_batch[jj,:,train_lengthMask[index]], train_target_batch[jj,:,train_lengthMask[index]])
                            jj += 1
                        MSE_trainbatch_linear_LOSS = torch.mean(MSE_train_linear_LOSS)
                    else: 
                        MSE_trainbatch_linear_LOSS = self.loss_fn(x_out_training_batch, train_target_batch)

            # dB Loss
            self.MSE_train_linear_epoch[ti] = MSE_trainbatch_linear_LOSS.item()
            self.MSE_train_dB_epoch[ti] = 10 * torch.log10(self.MSE_train_linear_epoch[ti])

            ##################
            ### Optimizing ###
            ##################

            # Before the backward pass, use the optimizer object to zero all of the
            # gradients for the variables it will update (which are the learnable
            # weights of the model). This is because by default, gradients are
            # accumulated in buffers( i.e, not overwritten) whenever .backward()
            # is called. Checkout docs of torch.autograd.backward for more details.

            # Backward pass: compute gradient of the loss with respect to model
            # parameters
            MSE_trainbatch_linear_LOSS.backward(retain_graph=True)

            # Calling the step function on an Optimizer makes an update to its
            # parameters
            self.optimizer.step()
            # self.scheduler.step(self.MSE_cv_dB_epoch[ti])

            #################################
            ### Validation Sequence Batch ###
            #################################

            # Cross Validation Mode
            self.model.eval()
            self.model.batch_size = self.CV_set_size
            # Init Hidden State
            self.model.init_hidden()
            with torch.no_grad():

                SysModel.T_test = cv_input.size()[-1] # T_test is the maximum length of the CV sequences

                x_out_cv_forward_batch = torch.empty([self.CV_set_size, SysModel.space_state_size, SysModel.T_test])
                x_out_cv_batch = torch.empty([self.CV_set_size, SysModel.space_state_size, SysModel.T_test])
                
                # Init Sequence
                if(randomInit):
                    if(cv_init==None):
                        self.model.InitSequence(\
                        SysModel.m1x_0.reshape(1,SysModel.space_state_size,1).repeat(self.CV_set_size,1,1), SysModel.T_test)
                    else:
                        self.model.InitSequence(cv_init, SysModel.T_test)                       
                else:
                    self.model.InitSequence(\
                        SysModel.m1x_0.reshape(1,SysModel.space_state_size,1).repeat(self.CV_set_size,1,1), SysModel.T_test)

                for t in range(0, SysModel.T_test):
                    x_out_cv_forward_batch[:, :, t] = torch.squeeze(self.model(torch.unsqueeze(cv_input[:, :, t],2), None, None, None))
                x_out_cv_batch[:, :, SysModel.T_test-1] = x_out_cv_forward_batch[:, :, SysModel.T_test-1] # backward smoothing starts from x_T|T
                self.model.InitBackward(torch.unsqueeze(x_out_cv_batch[:, :, SysModel.T_test-1],2)) 
                x_out_cv_batch[:, :, SysModel.T_test-2] = torch.squeeze(self.model(None, \
                    torch.unsqueeze(x_out_cv_forward_batch[:, :, SysModel.T_test-2],2), torch.unsqueeze(x_out_cv_forward_batch[:, :, SysModel.T_test-1],2),None))
                for t in range(SysModel.T_test-3, -1, -1):
                    x_out_cv_batch[:, :, t] = torch.squeeze(self.model(None, \
                        torch.unsqueeze(x_out_cv_forward_batch[:,:, t],2), torch.unsqueeze(x_out_cv_forward_batch[:,:, t+1],2),torch.unsqueeze(x_out_cv_batch[:,:, t+2],2)))                      

                # Compute CV Loss
                MSE_cvbatch_linear_LOSS = 0
                if(MaskOnState):
                    if self.args.randomLength:
                        for index in range(self.CV_set_size):
                            MSE_cv_linear_LOSS[index] = self.loss_fn(x_out_cv_batch[index,mask,cv_lengthMask[index]], cv_target[index,mask,cv_lengthMask[index]])
                        MSE_cvbatch_linear_LOSS = torch.mean(MSE_cv_linear_LOSS)
                    else:          
                        MSE_cvbatch_linear_LOSS = self.loss_fn(x_out_cv_batch[:,mask,:], cv_target[:,mask,:])
                else:
                    if self.args.randomLength:
                        for index in range(self.CV_set_size):
                            MSE_cv_linear_LOSS[index] = self.loss_fn(x_out_cv_batch[index,:,cv_lengthMask[index]], cv_target[index,:,cv_lengthMask[index]])
                        MSE_cvbatch_linear_LOSS = torch.mean(MSE_cv_linear_LOSS)
                    else:
                        MSE_cvbatch_linear_LOSS = self.loss_fn(x_out_cv_batch, cv_target)

                # dB Loss
                self.MSE_cv_linear_epoch[ti] = MSE_cvbatch_linear_LOSS.item()
                self.MSE_cv_dB_epoch[ti] = 10 * torch.log10(self.MSE_cv_linear_epoch[ti])
                
                if (self.MSE_cv_dB_epoch[ti] < self.MSE_cv_dB_opt):
                    self.MSE_cv_dB_opt = self.MSE_cv_dB_epoch[ti]
                    self.MSE_cv_idx_opt = ti
                    
                    # torch.save(self.model, path_results + 'best-model.pt')
                    torch.save(self.model.state_dict(), path_results + 'best-model-weights.pt')


            ########################
            ### Training Summary ###
            ########################
            print(ti, "MSE Training :", self.MSE_train_dB_epoch[ti], "[dB]", "MSE Validation :", self.MSE_cv_dB_epoch[ti],
                  "[dB]")
            
            
            if (ti > 1):
                d_train = self.MSE_train_dB_epoch[ti] - self.MSE_train_dB_epoch[ti - 1]
                d_cv = self.MSE_cv_dB_epoch[ti] - self.MSE_cv_dB_epoch[ti - 1]
                print("diff MSE Training :", d_train, "[dB]", "diff MSE Validation :", d_cv, "[dB]")

            print("Optimal idx:", self.MSE_cv_idx_opt, "Optimal :", self.MSE_cv_dB_opt, "[dB]")

        return [self.MSE_cv_linear_epoch, self.MSE_cv_dB_epoch, self.MSE_train_linear_epoch, self.MSE_train_dB_epoch]

    def NNTest(self, SysModel, test_input, test_target, path_results, MaskOnState=False,\
     randomInit=False,test_init=None,load_model=False,load_model_path=None,\
        test_lengthMask=None):

        self.N_T = test_input.shape[0]
        SysModel.T_test = test_input.size()[-1]
        self.MSE_test_linear_arr = torch.zeros([self.N_T])
        x_out_test_forward_batch = torch.zeros([self.N_T, SysModel.space_state_size, SysModel.T_test])
        x_out_test = torch.zeros([self.N_T, SysModel.space_state_size,SysModel.T_test])

        if MaskOnState:
            mask = torch.tensor([True,False,False])
            if SysModel.space_state_size == 2: 
                mask = torch.tensor([True,False])

        # MSE LOSS Function
        loss_fn = nn.MSELoss(reduction='mean')

        # Load model
        # if load_model:
        #     self.model = torch.load(load_model_path) 
        # else:
        #     self.model = torch.load(path_results+'best-model.pt')
        # Load model weights
        if load_model:
            model_weights = torch.load(load_model_path, map_location=self.device) 
        else:
            model_weights = torch.load(path_results+'best-model-weights.pt', map_location=self.device) 
        # Set the loaded weights to the model
        self.model.load_state_dict(model_weights)

        # Test mode
        self.model.eval()
        self.model.batch_size = self.N_T
        # Init Hidden State
        self.model.init_hidden()
        torch.no_grad()

        start = time.time()

        if (randomInit):
            self.model.InitSequence(test_init, SysModel.T_test)               
        else:
            self.model.InitSequence(SysModel.m1x_0.reshape(1,SysModel.space_state_size,1).repeat(self.N_T,1,1), SysModel.T_test)         
        
        for t in range(0, SysModel.T_test):
            x_out_test_forward_batch[:,:, t] = torch.squeeze(self.model(torch.unsqueeze(test_input[:,:, t],2), None, None, None))
        x_out_test[:,:, SysModel.T_test-1] = x_out_test_forward_batch[:,:, SysModel.T_test-1] # backward smoothing starts from x_T|T 
        self.model.InitBackward(torch.unsqueeze(x_out_test[:,:, SysModel.T_test-1],2)) 
        x_out_test[:,:, SysModel.T_test-2] = torch.squeeze(self.model(None, torch.unsqueeze(x_out_test_forward_batch[:,:, SysModel.T_test-2],2), torch.unsqueeze(x_out_test_forward_batch[:,:, SysModel.T_test-1],2),None))
        for t in range(SysModel.T_test-3, -1, -1):
            x_out_test[:,:, t] = torch.squeeze(self.model(None, torch.unsqueeze(x_out_test_forward_batch[:,:, t],2), torch.unsqueeze(x_out_test_forward_batch[:,:, t+1],2),torch.unsqueeze(x_out_test[:,:, t+2],2)))
        
        end = time.time()
        t = end - start

        # MSE loss
        for j in range(self.N_T):
            if(MaskOnState):
                if self.args.randomLength:
                    self.MSE_test_linear_arr[j] = loss_fn(x_out_test[j,mask,test_lengthMask[j]], test_target[j,mask,test_lengthMask[j]]).item()
                else:
                    self.MSE_test_linear_arr[j] = loss_fn(x_out_test[j,mask,:], test_target[j,mask,:]).item()
            else:
                if self.args.randomLength:
                    self.MSE_test_linear_arr[j] = loss_fn(x_out_test[j,:,test_lengthMask[j]], test_target[j,:,test_lengthMask[j]]).item()
                else:
                    self.MSE_test_linear_arr[j] = loss_fn(x_out_test[j,:,:], test_target[j,:,:]).item()
        
        # Average
        self.MSE_test_linear_avg = torch.mean(self.MSE_test_linear_arr)
        self.MSE_test_dB_avg = 10 * torch.log10(self.MSE_test_linear_avg)

        # Standard deviation
        self.MSE_test_linear_std = torch.std(self.MSE_test_linear_arr, unbiased=True)

        # Confidence interval
        self.test_std_dB = 10 * torch.log10(self.MSE_test_linear_std + self.MSE_test_linear_avg) - self.MSE_test_dB_avg

        # Print MSE and std
        str = self.modelName + "-" + "MSE Test:"
        print(str, self.MSE_test_dB_avg, "[dB]")
        str = self.modelName + "-" + "STD Test:"
        print(str, self.test_std_dB, "[dB]")
        # Print Run Time
        print("Inference Time:", t)

        return [self.MSE_test_linear_arr, self.MSE_test_linear_avg, self.MSE_test_dB_avg, x_out_test, t]

    def PlotTrain_RTS(self, MSE_KF_linear_arr, MSE_KF_dB_avg, MSE_RTS_linear_arr, MSE_RTS_dB_avg):
    
        self.Plot = Plot(self.folderName, self.modelName)

        self.Plot.NNPlot_epochs(self.train_set_size,self.num_epochs, self.batch_size, MSE_KF_dB_avg, MSE_RTS_dB_avg,
                                self.MSE_test_dB_avg, self.MSE_cv_dB_epoch, self.MSE_train_dB_epoch)

        self.Plot.NNPlot_Hist(MSE_KF_linear_arr, MSE_RTS_linear_arr, self.MSE_test_linear_arr)

    def count_parameters(self):
        return sum(p.numel() for p in self.model.parameters() if p.requires_grad)