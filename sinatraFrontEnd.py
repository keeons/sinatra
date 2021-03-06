import sinatraMainClass as sMC;
class sinatraFrontEnd(sMC.sinatraMainClass):
	def __init__(self):
		import numpy as np;
		self._sinatraMainClass__className = 'sinatraAudio';
		self.__trainingRows = np.zeros((1, 35));
		self.__trainingClass = np.zeros((1,1));
	def gatherTrainData(self, aD):
		import numpy as np;
		trainMatrix , thing1, thing2= self.segmentate(aD);
		rowNumber = len(trainMatrix[:,0]);
		classArray = np.ones(rowNumber) * aD.getlClass();
		temp = self.__trainingRows;
		newMatrix = np.zeros((rowNumber + len(temp[:,0]), len(temp[0,:]) ));
		newMatrix[0:(len(temp[:,0])),:] = temp;
		newMatrix[(len(temp[:,0])):, :] = trainMatrix;
		self.__trainingRows =newMatrix;
		temp = self.__trainingClass;
		newArray = np.zeros(len(temp) + len(classArray));
		newArray[0:len(temp)] = temp;
		newArray[len(temp):] = classArray;
		self.__trainingClass = newArray;
		return 1;
	def getTrainData(self):
		return self.__trainingRows, self.__trainingClass;
	def trainModel(self):
		from sklearn.neural_network import MLPClassifier;
		print("creating nn");
		nn = MLPClassifier(solver='lbgfs', alpha=1e-5, hidden_layer_sizes=(10,), random_state=1);
		print("starting training");
		nn.fit(self.__trainingRows, self.__trainingClass);
		print("finishing training");
		self.__nn = nn;
		return 1;
	def predict(self, aD):
		import numpy as np;
		predictMatrix, thing1, thing2 = self.segmentate(aD);
		res1 = np.zeros(len(predictMatrix[:,0]));
		for iter in range(len(predictMatrix[:,0])):
			row2predict = predictMatrix[iter,:];
			row2predict = row2predict.reshape(1,-1);
			res1[iter] = self.__nn.predict(row2predict);
		return res1;
	def normalize(self, aD):
		#
		#
		#
		#
		import sinatraIO;
		import numpy as np;
		aFAD = aD.getAudio();
		meanAFAD = np.mean(aFAD);
		stdAFAD = np.std(aFAD);
		aFAD = (aFAD - meanAFAD)/stdAFAD;
		aD.modAudio(aFAD);
		return 1;
	def segmentate(self, aD):
		#
		#	segmentate allows the Front End to find which are the pieces of the
		#	speech.
		#		1 - Clean the sound. We guess that high frequency
		#			sounds are not important for the accent. So,
		#			we need to perform a fourier transform, remove
		#			the high frequency terms, and come back to period through
		#			an inverse fourier transform.
		#		2 - Perform the derivatives of the amplitude. This is not a
		#			a trivial problem, since the spectrum is not regular, and
		#			differents minimums and maximums can be found. An approach
		#			could be to split the sound in intervals and perform the
		#			derivatives only with the maximum values of each interval.
		#
		#
		#	coeffCleaning : treshold under which fourier transformed frequencies
		#					are removed
		#	wS	: window-size
		import sinatraIO;
		import sinatraFilter;
		import numpy as np;
		filterBox = sinatraFilter.sinatraFiltersBox();
		coeffCleaning = 1.5;
		wS = 800;
		rowL = 10000;
		print("reading {0}".format(aD.getName()));
		self.normalize(aD);
		aD = aD.getAudio();
		print("\tremoving high frequencies");
		splitNumber = int(len(aD)/wS);
		aDTransformed = np.fft.fft(aD);
		meanADTransformed = np.mean(np.absolute(aDTransformed));
		aDTransformed[aDTransformed < coeffCleaning*meanADTransformed] = 0;
		aDTransformed[20000:] = 0;
		aDClean = np.fft.ifft(aDTransformed);
		aDClean = np.real(aDClean);
		#aDClean = aD;
		print("\tfiltering");
		#y,z,n = filterBox.entropyInWindow(aDClean, 750);
		#aDClean = aDClean*(n>=1);
		aCY = np.zeros(splitNumber); aCX = np.zeros(splitNumber);
		fD = np.zeros(splitNumber-2); sD = np.zeros(splitNumber-2);
		aCX, aCY = filterBox.filterMaxInWindow(aDClean, wS);
		aCY = aCY ** 2;
		print("\tprocessing first and second order derivatives");
		for derIter in range(1, splitNumber-2):
			fD[derIter] = (aCY[derIter+1]-aCY[derIter-1])/2;
			sD[derIter] = (1/4)*(aCY[derIter + 1] + aCY[derIter - 1] - 2*aCY[derIter]);
		print("\tsegmentating");
		statusMin = 0;
		statusMax = 0;
		cutPoints = [0, 0];
		rowControl = 1;
		matrixX = np.zeros(35);
		testArray = np.zeros(2);
		for sIter in range(2, splitNumber-3):
			if (fD[sIter]*fD[sIter+1]) <= 0:
				if (sD[sIter]+sD[sIter + 1]) > 0:
					cutPoints[statusMin]=aCX[sIter];
					statusMin = statusMin + 1;
				else:
					statusMax = 1;
			if (statusMin == 2) and (statusMax == 1):
				statusMin = 1;
				statusMax = 0;
				rowX = np.zeros(rowL);
				tokkenL = int(cutPoints[1]-cutPoints[0] + 1);
				if (tokkenL > 500) and (tokkenL < rowL):
					rowX[1:tokkenL] = aDClean[int(cutPoints[0]):int(cutPoints[1])];
					rowX = self.extractFeatures(rowX);
					tempTestArray = testArray;
					rowControl = rowControl + 1;
					testArray = np.zeros((rowControl, 2));
					testArray[0:(rowControl-1),:] = tempTestArray;
					testArray[rowControl-1, 0] = cutPoints[0];
					testArray[rowControl-1, 1] = cutPoints[1];
					tempMatrixX = matrixX;
					matrixX = np.zeros((rowControl, 35))
					matrixX[0:(rowControl - 1), :] = tempMatrixX;
					matrixX[(rowControl - 1), :] = rowX;
				cutPoints[0] = cutPoints[1];
		print("task completed");
		matrixX = matrixX[1:,:];
		testArray = testArray[1:,:];
		return matrixX, testArray, (rowControl - 1);

	def extractFeatures(self, tokken):
		import sinatraFilter as sF;
		import numpy as np;
		filterBox = sF.sinatraFiltersBox();
		wS = int(len(tokken) / 10);
		featureVector = list();
		featureBox = {};
		featureBox['mean'] = np.mean(tokken);
		featureBox['std'] = np.std(tokken);
		featureBox['len'] = len(tokken)
		featureBox['meanPositive'] = np.mean(tokken[tokken > 0]);
		featureBox['meanNegative'] = np.mean(tokken[tokken < 0]);
		x, featureBox['XmaxFilter'] = filterBox.filterMaxInWindow(tokken, wS);
		x, featureBox['XsoftMaxFilter'] = filterBox.softenedMaxWindow(tokken,wS);
		x, featureBox['XmeanLogAvWindow'] = filterBox.sumAbsWindow(tokken,wS);
		for fkeys, feature in sorted(featureBox.items()):
			if fkeys[0]=='X':
				for intIter in feature:
					featureVector.append(intIter);
			else:
				featureVector.append(feature);
		return featureVector;
