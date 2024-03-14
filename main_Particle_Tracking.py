import torch
import torch.nn as nn
from Smoothers.EKF_test import EKFTest
from Smoothers.Extended_RTS_Smoother_test import S_Test

from Simulations.Extended_sysmdl import SystemModel
from Simulations.utils import DataGen,Short_Traj_Split
import Simulations.config as config

from Pipelines.Pipeline_ERTS import Pipeline_ERTS as Pipeline
from Pipelines.Pipeline_EKF import Pipeline_EKF
from Pipelines.Pipeline_concat_models import Pipeline_twoRTSNets

from datetime import datetime

from RTSNet.RTSNet_nn import RTSNetNN
from Tools.utils import *
from Plot import Plot_extended as Plot
# batched model
# from Simulations.Particle_Tracking.parameters import m1x_0, m2x_0, m, n,\
# f, fInacc, h, hRotate, H_Rotate, H_Rotate_inv, Q_structure, R_structure
# # not batched model (for Jacobian calculation use)
# from Simulations.Lorenz_Atractor.parameters import Origin_f, Origin_fInacc, Origin_h, Origin_hRotate


print("Pipeline Start")
################
### Get Time ###
################
today = datetime.today()
now = datetime.now()
strToday = today.strftime("%m.%d.%y")
strNow = now.strftime("%H:%M:%S")
strTime = strToday + "_" + strNow
print("Current Time =", strTime)

##########################
### Parameter settings ###
##########################
system_config= CONFIG("/Users/amitmilstein/Documents/Ben_Gurion_Univ/MSc/TPC_RTSNet/TPC_Reconstruction/Simulations/Particle_Tracking/config.json")
args = config.general_settings()
system_config.use_cuda = False # use GPU or not
if system_config.use_cuda:
   if torch.cuda.is_available():
      device = torch.device('cuda')
      print("Using GPU")
      torch.set_default_tensor_type(torch.cuda.FloatTensor)
   else:
      raise Exception("No GPU found, please set args.use_cuda = False")
else:
    device = torch.device('cpu')
    print("Using CPU")

### dataset parameters ###################################################
offset = 0 # offset for the data
chop = False # whether to chop data sequences into shorter sequences


# only 'full' for data size case
switch = 'full'
# specify the path to save trained pass1 model
RTSNetPass1_path = "Simulations/Particle_Tracking/results/best-model-weights.pt"

### training parameters ##################################################
args.n_steps = 2000
args.n_batch = min(30, args.N_E)
args.lr = 1e-3
args.wd = 1e-3
path_results = 'RTSNet/'

# 1pass or 2pass
two_pass = False # if true: use two pass method, else: use one pass method

load_trained_pass1 = False # if True: load trained RTSNet pass1, else train pass1
# Save the dataset generated from testing RTSNet1 on train and CV data
load_dataset_for_pass2 = False # if True: load dataset generated from testing RTSNet1 on train and CV data
# Specify the path to save the dataset
DatasetPass1_path = "Simulations/Lorenz_Atractor/data/T100_Hrot1/2ndPass/partial/ResultofPass1_rq1030partial.pt" 

####################
###  load data   ###
####################
# print("Start Data Gen")
# DataGen(args, sys_model_gen, DatafolderName + dataFileName_gen)
print(f"Data Load : {os.path.basename(system_config.Dataset_path)}")
[train_set,CV_set, test_set] =  torch.load(system_config.Dataset_path)
 

#Extract Relevant Data on the Trajectories
system_config.delta_t = train_set[0].delta_t
system_config.data_source = train_set[0].data_src



train_set = train_set[:min(len(train_set),system_config.train_set_size)]
CV_set = CV_set[:min(len(CV_set),system_config.CV_set_size)]
test_set = CV_set[:min(len(test_set),system_config.test_set_size)]


# if chop: 
#    print("chop training data")    
#    [train_target, train_input, train_init] = Short_Traj_Split(train_target_long, train_input_long, args.T)
#    # [cv_target, cv_input] = Short_Traj_Split(cv_target, cv_input, args.T)
# else:
#    print("no chopping") 
#    train_target = train_target_long[:,:,0:args.T]
#    train_input = train_input_long[:,:,0:args.T] 
#    # cv_target = cv_target[:,:,0:args.T]
#    # cv_input = cv_input[:,:,0:args.T]  

print("trainset size:",len(train_set))
print("cvset size:",len(CV_set))
print("testset size:",len(test_set))

#######################
###  System model   ###
#######################
sys_model = SystemModel(f, h, system_config.state_vector_size, system_config.observation_vector_size)# parameters for GT


######################################
### Evaluate Filters and Smoothers ###
######################################
### Evaluate EKF true
# print("Evaluate EKF true")
# [MSE_EKF_linear_arr, MSE_EKF_linear_avg, MSE_EKF_dB_avg, EKF_KG_array, EKF_out] = EKFTest(args, sys_model, test_input, test_target)
# ### Evaluate EKF partial
# print("Evaluate EKF partial")
# [MSE_EKF_linear_arr_partial, MSE_EKF_linear_avg_partial, MSE_EKF_dB_avg_partial, EKF_KG_array_partial, EKF_out_partial] = EKFTest(args, sys_model_partial, test_input, test_target)

# ## Evaluate RTS true
print("Evaluate RTS true")
# [MSE_ERTS_linear_arr, MSE_ERTS_linear_avg, MSE_ERTS_dB_avg, ERTS_out] = S_Test(args, sys_model, test_input, test_target)
# ### Evaluate RTS partial
# print("Evaluate RTS partial")
# [MSE_ERTS_linear_arr_partial, MSE_ERTS_linear_avg_partial, MSE_ERTS_dB_avg_partial, ERTS_out_partial] = S_Test(args, sys_model_partial, test_input, test_target)

# ### Save trajectories
# trajfolderName = 'Smoothers' + '/'
# DataResultName = traj_resultName[0]
# EKF_sample = torch.reshape(EKF_out[0],[1,m,args.T_test])
# ERTS_sample = torch.reshape(ERTS_out[0],[1,m,args.T_test])
# PS_sample = torch.reshape(PS_out[0,:,:],[1,m,args.T_test])
# target_sample = torch.reshape(test_target[0,:,:],[1,m,args.T_test])
# input_sample = torch.reshape(test_input[0,:,:],[1,n,args.T_test])
# torch.save({
#             'EKF': EKF_sample,
#             'ERTS': ERTS_sample,
#             'ground_truth': target_sample,
#             'observation': input_sample,
#             }, trajfolderName+DataResultName)

#######################
### Evaluate RTSNet ###
#######################

######################
## RTSNet - 1 full ###
######################
if load_trained_pass1:
   print("Load RTSNet pass 1")
else:
   ## Build Neural Network
   print("RTSNet with full model info")
   RTSNet_model = RTSNetNN()
   RTSNet_model.NNBuild(sys_model,system_config)
   # ## Train Neural Network
   RTSNet_Pipeline = Pipeline(strTime, "RTSNet", "RTSNet",system_config)
   RTSNet_Pipeline.setssModel(sys_model)
   RTSNet_Pipeline.setModel(RTSNet_model)
   print("Number of trainable parameters for RTSNet:",sum(p.numel() for p in RTSNet_model.parameters() if p.requires_grad))
   RTSNet_Pipeline.setTrainingParams() 
   if(chop):
      [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, train_set, CV_set, path_results,randomInit=True,train_init=train_init)
   else:
      [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model, train_set, CV_set, path_results)
   ## Test Neural Network
   [MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out,RunTime] = RTSNet_Pipeline.NNTest(sys_model,test_set, path_results)
   # Save trained model
   torch.save(RTSNet_Pipeline.model.state_dict(), RTSNetPass1_path)
####################################################################################

if two_pass:
################################
## RTSNet - 2 with full info ###
################################
   if load_dataset_for_pass2:
      print("Load dataset for pass 2")
      [train_input_pass2, train_target_pass2, cv_input_pass2, cv_target_pass2, test_input, test_target] = torch.load(DatasetPass1_path)
      
      print("Data Shape for RTSNet pass 2:")
      print("testset state x size:",test_target.size())
      print("testset observation y size:",test_input.size())
      print("trainset state x size:",train_target_pass2.size())
      print("trainset observation y size:",len(train_input_pass2),train_input_pass2[0].size())
      print("cvset state x size:",cv_target_pass2.size())
      print("cvset observation y size:",len(cv_input_pass2),cv_input_pass2[0].size())  
   else:
      ### save result of RTSNet1 as dataset for RTSNet2 
      RTSNet_model_pass1 = RTSNetNN()
      RTSNet_model_pass1.NNBuild(sys_model, args)
      RTSNet_Pipeline_pass1 = Pipeline(strTime, "RTSNet", "RTSNet",system_config)
      RTSNet_Pipeline_pass1.setssModel(sys_model)
      RTSNet_Pipeline_pass1.setModel(RTSNet_model_pass1)
      ### Optional to test it on test-set, just for checking
      print("Test RTSNet pass 1 on test set")
      [_, _, _,rtsnet_out_test,_] = RTSNet_Pipeline_pass1.NNTest(sys_model, test_input, test_target, path_results,load_model=True,load_model_path=RTSNetPass1_path)

      print("Test RTSNet pass 1 on training set")
      [_, _, _,rtsnet_out_train,_] = RTSNet_Pipeline_pass1.NNTest(sys_model, train_input, train_target, path_results,load_model=True,load_model_path=RTSNetPass1_path)
      print("Test RTSNet pass 1 on cv set")
      [_, _, _,rtsnet_out_cv,_] = RTSNet_Pipeline_pass1.NNTest(sys_model, cv_input, cv_target, path_results,load_model=True,load_model_path=RTSNetPass1_path)
      

      train_input_pass2 = rtsnet_out_train
      train_target_pass2 = train_target
      cv_input_pass2 = rtsnet_out_cv
      cv_target_pass2 = cv_target

      torch.save([train_input_pass2, train_target_pass2, cv_input_pass2, cv_target_pass2, test_input, test_target], DatasetPass1_path)
   #######################################
   ## RTSNet_2passes with full info   
   # Build Neural Network
   print("RTSNet(with full model info) pass 2 pipeline start!")
   RTSNet_model = RTSNetNN()
   RTSNet_model.NNBuild(sys_model_pass2, args)
   print("Number of trainable parameters for RTSNet pass 2:",sum(p.numel() for p in RTSNet_model.parameters() if p.requires_grad))
   ## Train Neural Network
   RTSNet_Pipeline = Pipeline(strTime, "RTSNet", "RTSNet_pass2")
   RTSNet_Pipeline.setssModel(sys_model_pass2)
   RTSNet_Pipeline.setModel(RTSNet_model)
   RTSNet_Pipeline.setTrainingParams(args)
   #######################################
   [MSE_cv_linear_epoch, MSE_cv_dB_epoch, MSE_train_linear_epoch, MSE_train_dB_epoch] = RTSNet_Pipeline.NNTrain(sys_model_pass2, cv_input_pass2, cv_target_pass2, train_input_pass2, train_target_pass2, path_results)
   RTSNet_Pipeline.save()
   print("RTSNet pass 2 pipeline end!")
   #######################################
   # load trained Neural Network
   print("Concat two RTSNets and test")
   RTSNet_model1 = torch.load(RTSNetPass1_path)
   RTSNet_model2 = torch.load('RTSNet/best-model.pt')
   ## Set up Neural Network
   RTSNet_Pipeline_2passes = Pipeline_twoRTSNets(strTime, "RTSNet", "RTSNet")
   RTSNet_Pipeline_2passes.setModel(RTSNet_model1, RTSNet_model2)
   NumofParameter = RTSNet_Pipeline_2passes.count_parameters()
   print("Number of parameters for RTSNet with 2 passes: ",NumofParameter)
   ## Test Neural Network   
   [MSE_test_linear_arr, MSE_test_linear_avg, MSE_test_dB_avg,rtsnet_out,RunTime] = RTSNet_Pipeline_2passes.NNTest(sys_model, test_input, test_target, path_results)






