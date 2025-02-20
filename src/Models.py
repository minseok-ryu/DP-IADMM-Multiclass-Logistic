# import numpy as np #(activate this if CPU is used)
import cupy as np #(activate this if GPU is used)

import math
from Functions import *
import time

############################################## CLOSED FORM
def First_Block_Problem_ClosedForm(par):         
    ## Update W_val
    start = time.time()   
    Temp = np.sum(par.Z_val - par.Lambdas_val / par.rho, axis=0) / par.split_number    
    par.W_val = Temp
    end = time.time() 

    return par, end-start

def Second_Block_Problem_ClosedForm(par, x_train_agent, y_train_agent, iteration):  

    start = time.time()       
    ## Data Label Reformatting: Integer -> Binary
    num_data = []; y_train_Bin=[];
    for p in range(par.split_number):
        num_data.append( y_train_agent[p].shape[0] )                
        Temp = (np.arange(par.num_classes) == y_train_agent[p][...,None]).astype(int) ## Ip X K
        y_train_Bin.append(Temp)

    Z_Change = 0; Avg_Noise_Mag = 0; Grad_Time = 0; Noise_Time = 0; 
    for p in range(par.split_number):       
        start_grad = time.time()               
        temp_sum = np.zeros_like(par.Z_val[p])         
        for epoch in range(par.num_local_epoch):

            H=calculate_hypothesis(par.Z_val[p], x_train_agent[p]) ## I_p x K matrix  (see Functions.py)        
            grad = calculate_gradient(par, par.total_data, H, x_train_agent[p], y_train_Bin[p])   ## (see Functions.py)  
            end_grad = time.time()
            Grad_Time += end_grad - start_grad

            ## Generate Laplacian Noise
            tilde_xi = np.zeros((par.num_features, par.num_classes))    
            # if epoch == par.num_local_epoch - 1:
            if par.bar_eps_str != "infty":  
                start_noise = time.time()                             
                
                # tilde_xi = generate_laplacian_noise(par, H, par.total_data, x_train_agent[p], y_train_Bin[p], tilde_xi)  ## (see Functions.py)  
                
                
                if par.Instance =="MNIST":         
                    delta = 1e-6
                    c1 = math.sqrt( par.num_features*par.num_classes )  
                
                if par.Instance =="FEMNIST":         
                    delta = 1e-4
                    c1 = compute_local_ub_gradient(par, H, par.total_data, x_train_agent[p], y_train_Bin[p])
                
                # tilde_xi = generate_gaussian_noise(par, H, par.total_data, x_train_agent[p], y_train_Bin[p], tilde_xi, delta)  ## (see Functions.py)  

                ## global sensitivity
                sigma = math.sqrt(2*math.log(1.25/delta)) * c1 / (par.total_data * float(par.bar_eps_str))
                tilde_xi = np.random.normal( par.M, sigma, [par.num_features, par.num_classes])
 
                

                end_noise = time.time()                             
                Noise_Time += end_noise - start_noise
                Avg_Noise_Mag += np.mean(np.absolute(tilde_xi))  
                
            ## Update Z_val      
            if par.Algorithm =="ObjP":                   
                par.eta = float(par.a_str) / math.sqrt(iteration+1)  
                Z_Prev = par.Z_val[p]
                Temp = (1.0/(par.rho + (1.0/par.eta)))*(-grad + par.rho*par.W_val + par.Lambdas_val[p] - tilde_xi + (1.0/par.eta)*Z_Prev)                    
                Z_Change += np.absolute(Z_Prev - Temp)    
                par.Z_val[p] = bound_constraints(Temp, par.bound) 
                temp_sum += par.Z_val[p]


            if par.Algorithm =="ObjT":                    
                par.eta = float(par.a_str) / (iteration+1)*(iteration+1)
                Z_Prev = par.Z_val[p]                               
                Temp = (1.0/par.rho)*(-grad + par.rho*par.W_val + par.Lambdas_val[p] - tilde_xi)                         
                Temp = np.clip(Temp, Z_Prev - par.eta, Z_Prev + par.eta)   ## Trust-Region using the infinity norm
                Z_Change += np.absolute(Z_Prev  - Temp)              
                par.Z_val[p] = Temp

        par.Z_val[p] = temp_sum/par.num_local_epoch
                
            
    end = time.time()      

    Avg_Noise_Mag = Avg_Noise_Mag/par.split_number               
    return par, end-start, Avg_Noise_Mag, np.mean(Z_Change), Noise_Time, Grad_Time

def Base_First_Block_Problem_ClosedForm(par, x_train_agent, y_train_agent, Iteration):       
    
    start = time.time()   
    num_data = []; y_train_Bin=[];
    for p in range(par.split_number):
        num_data.append( y_train_agent[p].shape[0] )                
        Temp = (np.arange(par.num_classes) == y_train_agent[p][...,None]).astype(int) ## Ip X K
        y_train_Bin.append(Temp)
    
    Z_Change = 0; Avg_Noise_Mag = 0; Grad_Time = 0; Noise_Time = 0;  
    for p in range(par.split_number):                
        start_grad = time.time()                             
        temp_sum = np.zeros_like(par.Z_val[p])   
        for epoch in range(par.num_local_epoch):
            ## Hypothesis
            H=calculate_hypothesis(par.Z_val[p], x_train_agent[p]) ## I_p x K matrix        
            ## Gradient                                         
            grad = calculate_gradient(par, num_data[p], H, x_train_agent[p], y_train_Bin[p])  
            end_grad = time.time()
            Grad_Time += end_grad - start_grad

            ## Decide eta       
            if par.Instance =="MNIST":         
                delta = 1e-6
                c1 = math.sqrt( par.num_features*par.num_classes )
            if par.Instance =="FEMNIST":         
                delta = 1e-4
                c1 = compute_local_ub_gradient(par, H, par.total_data, x_train_agent[p], y_train_Bin[p])
                

            par.eta = calculate_eta_Base(par, num_data[p], Iteration, c1, delta)
            ## Update Z_val
            Temp = (1.0/(par.rho + (1.0/par.eta)))*(-grad + par.rho*par.W_val + par.Lambdas_val[p] + (1.0/par.eta)*par.Z_val[p])                                
            
            Z_Change += np.absolute(par.Z_val[p] - Temp)                                    
            
            ## bound constraints
            par.Z_val[p] = bound_constraints(Temp, par.bound)       
            
            ## Generate Matrix Normal Noise
            tilde_xi = np.zeros((par.num_features, par.num_classes))  
            if par.bar_eps_str != "infty":   
                start_noise = time.time()                                      
                tilde_xi = generate_matrix_normal_noise(par, num_data[p], tilde_xi, c1, delta)                        
                end_noise = time.time()                             
                Noise_Time += end_noise - start_noise

                par.Z_val[p] += tilde_xi

            Avg_Noise_Mag += np.mean(np.absolute(tilde_xi))        

            temp_sum += par.Z_val[p]


        par.Z_val[p] = temp_sum/par.num_local_epoch

    end = time.time()                 
    Avg_Noise_Mag = Avg_Noise_Mag/par.split_number
    return par, end-start, Avg_Noise_Mag, np.mean(Z_Change), Noise_Time, Grad_Time

def Base_Second_Block_Problem_ClosedForm(par):     
    
    ## Update W_val
    start = time.time()   
    Temp = np.sum(par.Z_val - par.Lambdas_val / par.rho, axis=0) / par.split_number              
    par.W_val = Temp
    end = time.time() 

    return par, end-start
 

