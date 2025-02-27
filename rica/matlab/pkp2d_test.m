%%
%
% Import files and extract data
%
% files = {'/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z2dchunk1_statex125_chi_ng6.mat'
% '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z2dchunk2_statex125_chi_ng6.mat'
% '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z2dchunk3_statex125_chi_ng6.mat'
% '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z2dchunk4_statex125_chi_ng6.mat'};

% Retrieve all the files in a directory
folder = '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z_ching6_statex424_chunk16';
filePattern = fullfile(folder, 'z2d_chunk*of*.mat');
files = dir(filePattern);

% files = {dirs.name};
ngfolder = '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/zng_ching6_statex424_chunk16';
ngfilePattern = fullfile(folder, 'zng2d_chunk*of*.mat');
ngfiles = dir(filePattern);
% ngdirs = dir('/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/zng_ching6_statex424_chunk16/zng2d_chunk*of*.mat');


% files = {'data/2d_zeta_fields/z2d_chunk{i}_statex{idxx}_chi_ng6'.format(i=i+1, idxx=idx[0])
%         '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z2dchunk2_statex125_chi_ng6.mat'
%         '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z2dchunk3_statex125_chi_ng6.mat'
%         '/fs/lustre/cita/haider/projects/pnong_ml/ica/data/2d_zeta_fields/z2dchunk4_statex125_chi_ng6.mat'};

% Number of 'observed mixtures' we want to provide RICA
nmix = length(files);
n = nmix;
% Number of features/latent components we want to extract
q = 2;

sizefield = 2000*2000;
nchunks = nmix;
sizechunk = sizefield/nchunks;
lside = sqrt(sizechunk);
nsidechunks = sqrt(nchunks);

%%
% Z = zeros(lside, lside, nmix);
Z = zeros(sizechunk, nmix);
for i = 1:n
    baseFileName = files(i).name;
    fullFileName = fullfile(files(i).folder, baseFileName);

    test     = load(fullFileName);
    y        = test.y; % The apostrophe denotes transpose.
    ogzeta(:, :, i) = y;
    % Z(:,:,i)   = y;
    testy = reshape(y, [], 1);
    Z(:,i)   = testy;
end
mixdata = Z;

rng default % For reproducibility

zetas = reshape(mixdata, lside, lside, nmix);


%%

figure
figtitle = sgtitle("Fig. 1: 'Observed' Chi^2_e nonG Zeta Chunks");
for i = 1:n
    subplot(nsidechunks,nsidechunks,i)
    imagesc(zetas(:,:,i))
    colormap('turbo');
    %clim([-0.0125, 0.025])
    colorbar
    title(['Zeta Chunk ',num2str(i)])
end

% saveas(gcf,'figs/plt-src_and_mix-chisq_zng.png')
exportgraphics(gcf,'figs/pkp2dzeta/plt-2dzeta_mix-chi_ng6.png')

%%
%
% Compare the mixtures with latent comps and prewhiten
%

% Plot the source latent comps and the observed mixtures
% figure
% for i = 1:6
%     subplot(2,6,i)
%     plot(S(:,i))
%     title(['Sound ',num2str(i)])

%     subplot(2,6,i+6)
%     if i <= nmix % only plot the mixtures to be used by RICA
%         plot(mixdata(:,i))
%         title(['Mix ',num2str(i)])
%     end
% end

% Prewhiten the mixed data
mixdata = prewhiten(mixdata);






%%
%
% Optimize parameters
%

% Using the same mixed data as above
Xtrain = mixdata;

% To remove sources of variation, fix an initial transform weight matrix.
W = randn(n,q);

% Create hyperparameters for the objective function.
iterlim = optimizableVariable('iterlim',[5,1e15],'Type','integer');
lambda = optimizableVariable('lambda',[100,101]);
gradtol = optimizableVariable('gradtol',[1e-12, 1e-6]);
steptol = optimizableVariable('steptol', [1e-12, 1e-6]);
vars = [iterlim, lambda, gradtol, steptol];

% Run the optimization without the warnings that occur when the internal optimizations do not run to completion. Run for 60 iterations instead of the default 30 to give the optimization a better chance of locating a good value.
maxevals = 40;
% warning('off','stats:classreg:learning:fsutils:Solver:LBFGSUnableToConverge');
results = bayesopt(@(x) filterica(x,Xtrain,W,q,nmix),vars, ...
    'UseParallel',true,'MaxObjectiveEvaluations',maxevals, ...
    'AcquisitionFunctionName','expected-improvement-plus', ...
    'IsObjectiveDeterministic', false);
warning('on','stats:classreg:learning:fsutils:Solver:LBFGSUnableToConverge');

% Extract best params:
optiterlim = results.XAtMinObjective.iterlim;
optlambda= results.XAtMinObjective.lambda;
optgradtol = results.XAtMinObjective.gradtol;
optsteptol = results.XAtMinObjective.steptol;

data = load('SampleImagePatches');
size(data.X)








%%
%
% Apply RICA
%
% iterlim = 1e14;
% gradtol = 1e-10;
% steptol = 1e-10;
iterlim = optiterlim;
lambda = optlambda;
lambda = 10;
gradtol = optgradtol;
steptol = optsteptol;
q = q;

% Model = rica(mixdata,q,'NonGaussianityIndicator',ones(6,1)); % create rica model
Model = rica(mixdata, q, ...
        'Standardize', true, 'NonGaussianityIndicator',ones(q,1), 'VerbosityLevel', 1, ...
        'Lambda', lambda, 'IterationLimit', iterlim, ...
        'GradientTolerance', gradtol, 'StepTolerance', steptol)
% Model = rica(mixdata,q, 'InitialTransformWeights',Model.TransformWeights, 'Lambda', lambda, 'NonGaussianityIndicator',ones(6,1), 'VerbosityLevel', 1, 'GradientTolerance',1e-9, 'StepTolerance',1e-9, 'IterationLimit',1e6)
ogunmixed = transform(Model,mixdata); % extract the unmixed comps


for i = 1:q
    ogunmixed(:,i) = ogunmixed(:,i)/norm(ogunmixed(:,i))*norm(mixdata(:,1));
end
unmixed = reshape(ogunmixed, lside, lside, q) / 400;





%%
% Plot the extracted/unmixed signals
%
f = figure;
w = 200*n;
h = 150*2;
f.Position = [5 5 w h];
figtitle = sgtitle('Fig. 2: Prelim RICA unmixed Chi^2_e nonG Zeta');
for i = 1:n
    subplot(2,n,i)
    imagesc(zetas(:,:,i))
    colormap('turbo');
    clim([-0.01, 0.0225])
    colorbar
    title(['Observed Mixture (Zeta) ',num2str(i)])

    subplot(2,n,i+n)
    if i <= q % only plot the mixtures to be used by RICA
        imagesc(unmixed(:,:,i))
        colormap('turbo');
        clim([-0.01, 0.0225])
        colorbar
        title(['Unmixed IC ',num2str(i)])
    end
end





%%
% Fix parity and reorder unmixed

% Fix parity of unmixed signals:
unmixedre = zeros(lside, lside, q);
unmixedre(:,:,1) = -unmixed(:,:,1); 
unmixedre(:,:,2) = unmixed(:,:,2); 
% unmixedre(:,:,3) = unmixed(:,:,3);
% unmixedre(:,:,4) = -unmixed(:,:,4);

% Reorder the unmixed signals correctly
% unmixedfinal = unmixedre(:,:,[3,2,4,1]);
unmixedfinal = unmixedre(:,:,[1,2]);
zetasre = zetas(:,:,[1, 2]);
% zetasre = zetas;

% Rescale unmixed signals
for i = 1:q
    unmixedfinal(:,:,i) = unmixedfinal(:,:,i)/norm(unmixedfinal(:,:,i))*norm(zetasre(:,:,i));
end




%%
% Plot the extracted/unmixed signals in the right order

f = figure;
f.Position = [5 5 800 400];
figtitle = sgtitle(sprintf("Fig. 3: RICA unmixed Chi^2_e nonG Zeta: Separation with q=%d ICs.", q));

for i = 1:q
    subplot(2,q,i)
    imagesc(zetasre(:,:,i))
    colormap('turbo');
    clim([-0.01, 0.0225])
    colorbar
    title(['Observed Mixture (Zeta) ',num2str(i)])
    hold on;

    subplot(2,q,i+q)
    if i <= q % only plot the mixtures to be used by RICA
        imagesc(unmixedfinal(:,:,i))
        colormap('turbo');
        clim([-0.01, 0.0225])
        colorbar
        title(['Unmixed IC ',num2str(i)])
    end
    hold on;
end
hold off;
exportgraphics(gcf, sprintf('figs/pkp2dzeta/pkp-2dzetachunks%d_rica_unmix-chi_ng6_q%d.png', nchunks, q))





%%
%
% RICA Params
%
ricafit = Model.FitInfo;
ricafititer = ricafit.Iteration;
ricafitobj = ricafit.Objective;
ricafitobjmin = min(ricafitobj);

figure
plot(ricafititer, ricafitobj)

Model.TransformWeights;
% display(ricafitobj)`


%%
%
% Objective function for bayesopt (optimizer for parameters)
%

% Feature extraction functions have these tuning parameters:
%
% Iteration limit
% Function, either rica or sparsefilt
% Parameter Lambda
% Number of learned features q
%
% To search among the available parameters effectively, try bayesopt. Use the following objective function, which includes parameters passed from the workspace.

function objective = filterica(x,Xtrain,winit,q,nmix)

    initW = winit(1:nmix,1:q);

    Mdl = rica(Xtrain,q,'Lambda',x.lambda,'IterationLimit',x.iterlim, ...
        'InitialTransformWeights',initW,'Standardize',true, ...
        'GradientTolerance', x.gradtol, 'StepTolerance',x.steptol);
    
    NewX = transform(Mdl,Xtrain);
    ricafit = Mdl.FitInfo;
    ricafitobj = ricafit.Objective;
    objective = min(ricafitobj);

end


%%
%
% Prewhiten function
%

function Z = prewhiten(X)
    % X = N-by-P matrix for N observations and P predictors
    % Z = N-by-P prewhitened matrix
    
        % 1. Size of X.
        [N,P] = size(X);
        assert(N >= P);
    
        % 2. SVD of covariance of X. We could also use svd(X) to proceed but N
        % can be large and so we sacrifice some accuracy for speed.
        [U,Sig] = svd(cov(X));
        Sig     = diag(Sig);
        Sig     = Sig(:)';
    
        % 3. Figure out which values of Sig are non-zero.
        tol = eps(class(X));
        idx = (Sig > max(Sig)*tol);
        assert(~all(idx == 0));
    
        % 4. Get the non-zero elements of Sig and corresponding columns of U.
        Sig = Sig(idx);
        U   = U(:,idx);
    
        % 5. Compute prewhitened data.
        mu = mean(X,1);
        Z = bsxfun(@minus,X,mu);
        Z = bsxfun(@times,Z*U,1./sqrt(Sig));
end


