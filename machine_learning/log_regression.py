import torch
import torch.nn as nn
import numpy as np
from sklearn import datasets
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from matplotlib import pyplot as plt


# (0) prep data
bc = datasets.load_breast_cancer()  # brest cancer binary classification dataset with 569 samples à 30 features
X, y = bc.data, bc.target

n_samples, n_features = X.shape

# split and transform data (set mean and offset to '0' and define uniform variance)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1234)  # split 20% from total data as training data
sc = StandardScaler()
X_train = sc.fit_transform(X_train)
X_test = sc.transform(X_test)

# convert data to torch tensors with dtype=float32
X_train = torch.from_numpy(X_train.astype(np.float32))
X_test = torch.from_numpy(X_test.astype(np.float32))
y_train = torch.from_numpy(y_train.astype(np.float32))
y_test = torch.from_numpy(y_test.astype(np.float32))

# cast output to 1-col vector
y_train = y_train.view(-1 ,1)
y_test = y_test.view(-1, 1)


# (1) model: f(X) = [weigths]x + [biases] with sigmoid function
class LogisticRegression(nn.Module):
    def __init__(self, n_input_features):
        super(LogisticRegression, self).__init__()
        self.linear = nn.Linear(n_input_features, 1)
    
    def forward(self, x):
        y_predicted = torch.sigmoid(self.linear(x))
        return y_predicted

model = LogisticRegression(n_features)


# (2) loss and optimizer
learning_rate = 1
criterion = nn.BCELoss()  # binary cross entropy loss
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)


# (3) training loop
n_epochs = 1000
for epoch in range(n_epochs):
    # forward pass
    y_predicted = model(X_train)
    loss = criterion(y_predicted, y_train)

    # backward pass
    loss.backward()

    # update parameters, zero gradients
    optimizer.step()
    optimizer.zero_grad()

    if (epoch + 1) % 100 == 0:
        print(f'Epoch {str(epoch + 1).zfill(4)} | Loss: {loss.item():.6f}')


# (4) evaluation
with torch.no_grad():  # not part of computational graph
    y_predicted = model(X_test)
    y_predicted_cls = y_predicted.round()
    accuracy = y_predicted_cls.eq(y_test).sum() / y_test.shape[0]

    print(f'\nAccuracy: {accuracy:.6f}')

plt.plot(X_test, y_test, 'bo', markersize=1.5)
plt.plot(X_test, y_predicted_cls, 'ro', markersize=1.5)
plt.show()