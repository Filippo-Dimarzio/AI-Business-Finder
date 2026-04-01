"""
ML classifier module for the Business Finder system.
Uses machine learning to classify businesses as having no website/social media presence.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import joblib
import os
from loguru import logger
from database import get_session, Business, ProcessingLog
from datetime import datetime

class BusinessClassifier:
    """Main class for ML-based business classification"""
    
    def __init__(self):
        self.session = get_session()
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
        
        # Feature engineering parameters
        self.business_types = ['restaurant', 'cafe', 'takeaway', 'bakery', 'pub', 'bar', 'fast_food']
        self.city_sizes = {
            'london': 'large', 'manchester': 'large', 'birmingham': 'large', 'liverpool': 'large',
            'leeds': 'medium', 'sheffield': 'medium', 'bristol': 'medium', 'newcastle': 'medium',
            'nottingham': 'medium', 'leicester': 'medium'
        }
    
    def extract_features(self, business: Business) -> Dict[str, float]:
        """
        Extract features from business data for ML model
        
        Args:
            business: Business object
            
        Returns:
            Dictionary of features
        """
        features = {}
        
        # Basic business information
        features['name_length'] = len(business.name) if business.name else 0
        features['address_length'] = len(business.address) if business.address else 0
        features['has_phone'] = 1.0 if business.phone else 0.0
        features['has_city'] = 1.0 if business.city else 0.0
        features['has_postcode'] = 1.0 if business.postcode else 0.0
        
        # Google Places data (if available)
        if 'Google Places API' in (business.sources or []):
            features['has_google_places'] = 1.0
            features['has_google_photos'] = 1.0 if getattr(business, 'google_photos_count', 0) > 0 else 0.0
            features['has_google_reviews'] = 1.0 if getattr(business, 'google_review_count', 0) > 0 else 0.0
            features['google_rating'] = float(getattr(business, 'google_rating', 0))
        else:
            features['has_google_places'] = 0.0
            features['has_google_photos'] = 0.0
            features['has_google_reviews'] = 0.0
            features['google_rating'] = 0.0
        
        # Business type indicators
        business_name_lower = business.name.lower() if business.name else ""
        for business_type in self.business_types:
            features[f'is_{business_type}'] = 1.0 if business_type in business_name_lower else 0.0
        
        # City size indicator
        city_lower = business.city.lower() if business.city else ""
        city_size = self.city_sizes.get(city_lower, 'small')
        features['city_size_large'] = 1.0 if city_size == 'large' else 0.0
        features['city_size_medium'] = 1.0 if city_size == 'medium' else 0.0
        features['city_size_small'] = 1.0 if city_size == 'small' else 0.0
        
        # Data source indicators
        sources = business.sources if business.sources else []
        features['source_count'] = len(sources)
        features['has_google_places'] = 1.0 if 'Google Places API' in sources else 0.0
        features['has_osm'] = 1.0 if 'OpenStreetMap' in sources else 0.0
        features['has_csv'] = 1.0 if any('CSV' in source for source in sources) else 0.0
        
        # Website and social media status
        features['website_present'] = 1.0 if business.website_present else 0.0
        features['social_present'] = 1.0 if business.social_present else 0.0
        
        # Business name characteristics
        if business.name:
            features['name_has_numbers'] = 1.0 if any(char.isdigit() for char in business.name) else 0.0
            features['name_has_special_chars'] = 1.0 if any(char in "&'()" for char in business.name) else 0.0
            features['name_word_count'] = len(business.name.split())
        else:
            features['name_has_numbers'] = 0.0
            features['name_has_special_chars'] = 0.0
            features['name_word_count'] = 0.0
        
        # Address characteristics
        if business.address:
            features['address_has_numbers'] = 1.0 if any(char.isdigit() for char in business.address) else 0.0
            features['address_word_count'] = len(business.address.split())
        else:
            features['address_has_numbers'] = 0.0
            features['address_word_count'] = 0.0
        
        # Time-based features
        if business.created_at:
            features['days_since_created'] = (datetime.utcnow() - business.created_at).days
        else:
            features['days_since_created'] = 0.0
        
        if business.last_checked_date:
            features['days_since_last_check'] = (datetime.utcnow() - business.last_checked_date).days
        else:
            features['days_since_last_check'] = 0.0
        
        return features
    
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from database
        
        Returns:
            Tuple of (features, labels)
        """
        logger.info("Preparing training data from database")
        
        # Get all businesses with human review labels
        businesses = self.session.query(Business).filter(
            Business.human_review.isnot(None)
        ).all()
        
        if len(businesses) < 10:
            logger.warning("Not enough labeled data for training. Need at least 10 examples.")
            return np.array([]), np.array([])
        
        features_list = []
        labels = []
        
        for business in businesses:
            try:
                        # Extract features as dictionary
                features = self.extract_features(business)
                features_list.append(features)  # Store feature dictionary
                
                # Create label (1 if no website/social, 0 if has website/social)
                if business.human_review == 'approved':
                    label = 1.0  # No website/social
                else:
                    label = 0.0  # Has website/social
                
                labels.append(label)
                
            except Exception as e:
                logger.error(f"Error extracting features for business {business.id}: {e}")
                continue
        
        if not features_list:
            logger.error("No features extracted from training data")
            return np.array([]), np.array([])
        
        # Convert features to consistent format
        feature_names = []
        feature_matrix = []
        
        if features_list:
            # Get unique feature names from all examples
            feature_names = list(set().union(*[set(f.keys()) for f in features_list]))
            feature_names.sort()  # Ensure consistent order
            
            # Convert dict to array with consistent feature order
            for features in features_list:
                feature_vector = [features.get(fname, 0.0) for fname in feature_names]
                feature_matrix.append(feature_vector)
            
            self.feature_names = feature_names
            X = np.array(feature_matrix)
            y = np.array(labels)
            
            logger.info(f"Prepared training data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Train ML model on prepared data
        
        Args:
            X: Feature matrix
            y: Labels
            
        Returns:
            Dictionary of model performance metrics
        """
        if len(X) == 0:
            logger.error("No training data available")
            return {}
        
        logger.info("Training ML model")
        
        # Split data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Try multiple models
        models = {
            'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'lightgbm': lgb.LGBMClassifier(random_state=42, verbose=-1)
        }
        
        best_model = None
        best_score = 0
        best_model_name = ""
        
        for model_name, model in models.items():
            try:
                # Train model
                model.fit(X_train_scaled, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test_scaled)
                y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
                
                # Calculate metrics
                auc_score = roc_auc_score(y_test, y_pred_proba)
                
                logger.info(f"{model_name} - AUC: {auc_score:.3f}")
                
                if auc_score > best_score:
                    best_score = auc_score
                    best_model = model
                    best_model_name = model_name
                    
            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
                continue
        
        if best_model is None:
            logger.error("No model could be trained successfully")
            return {}
        
        # Store the best model
        self.model = best_model
        
        # Final evaluation
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        # Calculate final metrics
        auc_score = roc_auc_score(y_test, y_pred_proba)
        accuracy = (y_pred == y_test).mean()
        
        # Cross-validation score
        cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5, scoring='roc_auc')
        
        metrics = {
            'model_name': best_model_name,
            'auc_score': auc_score,
            'accuracy': accuracy,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'n_samples': len(X),
            'n_features': X.shape[1]
        }
        
        logger.info(f"Model training completed. Best model: {best_model_name}")
        logger.info(f"AUC: {auc_score:.3f}, Accuracy: {accuracy:.3f}")
        
        return metrics
    
    def predict_business(self, business: Business) -> Tuple[bool, float]:
        """
        Predict if a business has no website/social media presence
        
        Args:
            business: Business object to predict
            
        Returns:
            Tuple of (prediction, confidence_score)
        """
        if self.model is None:
            logger.error("Model not trained. Cannot make predictions.")
            return False, 0.0
        
        try:
            # Extract features
            features = self.extract_features(business)
            feature_values = list(features.values())
            
            # Scale features
            X_scaled = self.scaler.transform([feature_values])
            
            # Make prediction
            prediction = self.model.predict(X_scaled)[0]
            confidence = self.model.predict_proba(X_scaled)[0][1]  # Probability of class 1
            
            return bool(prediction), float(confidence)
            
        except Exception as e:
            logger.error(f"Error predicting for business {business.id}: {e}")
            return False, 0.0
    
    def classify_all_businesses(self) -> int:
        """
        Classify all businesses in the database
        
        Returns:
            Number of businesses processed
        """
        if self.model is None:
            logger.error("Model not trained. Cannot classify businesses.")
            return 0
        
        logger.info("Starting classification of all businesses")
        
        businesses = self.session.query(Business).all()
        processed_count = 0
        
        for business in businesses:
            try:
                # Skip if already classified recently
                if (business.no_website_no_social is not None and 
                    business.last_checked_date and 
                    (datetime.utcnow() - business.last_checked_date).days < 1):
                    continue
                
                # Make prediction
                prediction, confidence = self.predict_business(business)
                
                # Update business record
                business.no_website_no_social = prediction
                business.confidence_score = confidence
                business.last_checked_date = datetime.utcnow()
                
                processed_count += 1
                
                # Log progress
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} businesses")
                
                # Log the result
                self._log_processing(
                    business_id=business.id,
                    process_type="classification",
                    status="success",
                    message=f"Classification completed: {prediction} (confidence: {confidence:.3f})",
                    details={"prediction": prediction, "confidence": confidence}
                )
                
            except Exception as e:
                logger.error(f"Error classifying business {business.id}: {e}")
                self._log_processing(
                    business_id=business.id,
                    process_type="classification",
                    status="error",
                    message=f"Error classifying business: {str(e)}"
                )
        
        self.session.commit()
        logger.info(f"Successfully classified {processed_count} businesses")
        return processed_count
    
    def get_high_confidence_predictions(self, threshold: float = None) -> List[Business]:
        """
        Get businesses with high confidence predictions
        
        Args:
            threshold: Confidence threshold (defaults to class threshold)
            
        Returns:
            List of businesses with high confidence predictions
        """
        if threshold is None:
            threshold = self.confidence_threshold
        
        businesses = self.session.query(Business).filter(
            Business.confidence_score >= threshold,
            Business.no_website_no_social == True
        ).all()
        
        return businesses
    
    def save_model(self, filepath: str = "business_classifier_model.pkl"):
        """
        Save trained model to file
        
        Args:
            filepath: Path to save model
        """
        if self.model is None:
            logger.error("No model to save")
            return
        
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'confidence_threshold': self.confidence_threshold
            }
            
            joblib.dump(model_data, filepath)
            logger.info(f"Model saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self, filepath: str = "business_classifier_model.pkl"):
        """
        Load trained model from file
        
        Args:
            filepath: Path to load model from
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"Model file not found: {filepath}")
                return
            
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.confidence_threshold = model_data.get('confidence_threshold', 0.7)
            
            logger.info(f"Model loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def _log_processing(self, business_id: Optional[int], process_type: str, 
                       status: str, message: str, details: Dict = None):
        """Log processing activities"""
        log_entry = ProcessingLog(
            business_id=business_id,
            process_type=process_type,
            status=status,
            message=message,
            details=details
        )
        self.session.add(log_entry)
    
    def run_rule_based_classification(self):
        """Run rule-based classification as fallback"""
        businesses = self.session.query(Business).all()
        processed_count = 0
        
        for business in businesses:
            try:
                # Simple rule-based classification
                has_website = business.website_present or False
                has_social = business.social_present or False
                
                # Classify as no website/social if both are False
                business.no_website_no_social = not has_website and not has_social
                
                # Calculate confidence based on data completeness
                confidence = 0.5  # Base confidence
                if business.address:
                    confidence += 0.1
                if business.phone:
                    confidence += 0.1
                if business.sources and len(business.sources) > 1:
                    confidence += 0.1
                if business.digital_presence_details:
                    confidence += 0.2
                
                business.confidence_score = min(confidence, 1.0)
                business.last_checked_date = datetime.utcnow()
                processed_count += 1
                
                if processed_count % 100 == 0:
                    self.session.commit()
                    logger.info(f"Processed {processed_count} businesses")
            
            except Exception as e:
                logger.error(f"Error classifying business {business.id}: {e}")
                continue
        
        self.session.commit()
        logger.info(f"Rule-based classification completed for {processed_count} businesses")
        return processed_count

    def close(self):
        """Close database session"""
        self.session.close()

# Example usage and testing
if __name__ == "__main__":
    classifier = BusinessClassifier()
    
    # Prepare training data
    # X, y = classifier.prepare_training_data()
    
    # Train model
    # if len(X) > 0:
    #     metrics = classifier.train_model(X, y)
    #     print(f"Model performance: {metrics}")
    
    # Classify all businesses
    # classifier.classify_all_businesses()
    
    # Get high confidence predictions
    # high_confidence = classifier.get_high_confidence_predictions()
    # print(f"Found {len(high_confidence)} high confidence predictions")
    
    classifier.close()
