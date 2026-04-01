"""
Export module for the Business Finder system.
Handles CSV and JSON export of business data.
"""

import csv
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from database import get_session, Business

class BusinessExporter:
    """Main class for exporting business data"""
    
    def __init__(self):
        self.session = get_session()
    
    def export_to_csv(self, 
                      output_path: str = "businesses_export.csv",
                      filters: Optional[Dict] = None) -> str:
        """
        Export businesses to CSV format
        
        Args:
            output_path: Path to save CSV file
            filters: Optional filters to apply
            
        Returns:
            Path to exported file
        """
        logger.info(f"Starting CSV export to {output_path}")
        
        try:
            # Get businesses with filters
            businesses = self._get_filtered_businesses(filters)
            
            # Define CSV headers
            headers = [
                'id', 'name', 'address', 'phone', 'city', 'postcode',
                'website_present', 'website_url', 'social_present', 'social_links',
                'no_website_no_social', 'confidence_score', 'sources',
                'last_checked_date', 'human_review', 'human_reviewer',
                'human_review_date', 'notes', 'created_at', 'updated_at'
            ]
            
            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for business in businesses:
                    row = {
                        'id': business.id,
                        'name': business.name,
                        'address': business.address or '',
                        'phone': business.phone or '',
                        'city': business.city or '',
                        'postcode': business.postcode or '',
                        'website_present': business.website_present or False,
                        'website_url': business.website_url or '',
                        'social_present': business.social_present or False,
                        'social_links': json.dumps(business.social_links) if business.social_links else '',
                        'no_website_no_social': business.no_website_no_social or False,
                        'confidence_score': business.confidence_score or 0,
                        'sources': '; '.join(business.sources) if business.sources else '',
                        'last_checked_date': business.last_checked_date.isoformat() if business.last_checked_date else '',
                        'human_review': business.human_review or '',
                        'human_reviewer': business.human_reviewer or '',
                        'human_review_date': business.human_review_date.isoformat() if business.human_review_date else '',
                        'notes': business.notes or '',
                        'created_at': business.created_at.isoformat(),
                        'updated_at': business.updated_at.isoformat()
                    }
                    writer.writerow(row)
            
            logger.info(f"Successfully exported {len(businesses)} businesses to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            raise
    
    def export_to_json(self, 
                       output_path: str = "businesses_export.json",
                       filters: Optional[Dict] = None) -> str:
        """
        Export businesses to JSON format
        
        Args:
            output_path: Path to save JSON file
            filters: Optional filters to apply
            
        Returns:
            Path to exported file
        """
        logger.info(f"Starting JSON export to {output_path}")
        
        try:
            # Get businesses with filters
            businesses = self._get_filtered_businesses(filters)
            
            # Convert to JSON-serializable format
            json_data = []
            for business in businesses:
                business_data = {
                    'id': business.id,
                    'name': business.name,
                    'address': business.address,
                    'phone': business.phone,
                    'city': business.city,
                    'postcode': business.postcode,
                    'website_present': business.website_present,
                    'website_url': business.website_url,
                    'social_present': business.social_present,
                    'social_links': business.social_links,
                    'no_website_no_social': business.no_website_no_social,
                    'confidence_score': business.confidence_score,
                    'sources': business.sources,
                    'last_checked_date': business.last_checked_date.isoformat() if business.last_checked_date else None,
                    'human_review': business.human_review,
                    'human_reviewer': business.human_reviewer,
                    'human_review_date': business.human_review_date.isoformat() if business.human_review_date else None,
                    'notes': business.notes,
                    'created_at': business.created_at.isoformat(),
                    'updated_at': business.updated_at.isoformat()
                }
                json_data.append(business_data)
            
            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully exported {len(businesses)} businesses to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            raise
    
    def export_approved_only(self, 
                           output_path: str = "approved_businesses.csv",
                           format: str = "csv") -> str:
        """
        Export only approved businesses (those with no website/social media)
        
        Args:
            output_path: Path to save export file
            format: Export format ('csv' or 'json')
            
        Returns:
            Path to exported file
        """
        filters = {
            'human_review': 'approved',
            'no_website_no_social': True
        }
        
        if format.lower() == 'csv':
            return self.export_to_csv(output_path, filters)
        else:
            return self.export_to_json(output_path, filters)
    
    def export_high_confidence(self, 
                             output_path: str = "high_confidence_businesses.csv",
                             confidence_threshold: float = 0.8,
                             format: str = "csv") -> str:
        """
        Export high confidence predictions
        
        Args:
            output_path: Path to save export file
            confidence_threshold: Minimum confidence score
            format: Export format ('csv' or 'json')
            
        Returns:
            Path to exported file
        """
        filters = {
            'confidence_score_min': confidence_threshold,
            'no_website_no_social': True
        }
        
        if format.lower() == 'csv':
            return self.export_to_csv(output_path, filters)
        else:
            return self.export_to_json(output_path, filters)
    
    def export_summary_report(self, output_path: str = "summary_report.json") -> str:
        """
        Export summary statistics and report
        
        Args:
            output_path: Path to save report file
            
        Returns:
            Path to exported file
        """
        logger.info(f"Generating summary report to {output_path}")
        
        try:
            # Get all businesses
            all_businesses = self.session.query(Business).all()
            
            # Calculate statistics
            total_businesses = len(all_businesses)
            pending_review = len([b for b in all_businesses if not b.human_review])
            approved = len([b for b in all_businesses if b.human_review == 'approved'])
            rejected = len([b for b in all_businesses if b.human_review == 'rejected'])
            
            # Website and social media statistics
            has_website = len([b for b in all_businesses if b.website_present])
            has_social = len([b for b in all_businesses if b.social_present])
            no_website_no_social = len([b for b in all_businesses if b.no_website_no_social])
            
            # Confidence statistics
            high_confidence = len([b for b in all_businesses if b.confidence_score and b.confidence_score >= 0.8])
            medium_confidence = len([b for b in all_businesses if b.confidence_score and 0.5 <= b.confidence_score < 0.8])
            low_confidence = len([b for b in all_businesses if b.confidence_score and b.confidence_score < 0.5])
            
            # Source statistics
            source_counts = {}
            for business in all_businesses:
                if business.sources:
                    for source in business.sources:
                        source_counts[source] = source_counts.get(source, 0) + 1
            
            # Create summary report
            report = {
                'export_date': datetime.utcnow().isoformat(),
                'total_businesses': total_businesses,
                'review_status': {
                    'pending': pending_review,
                    'approved': approved,
                    'rejected': rejected
                },
                'digital_presence': {
                    'has_website': has_website,
                    'has_social_media': has_social,
                    'no_website_no_social': no_website_no_social
                },
                'confidence_distribution': {
                    'high_confidence': high_confidence,
                    'medium_confidence': medium_confidence,
                    'low_confidence': low_confidence
                },
                'source_distribution': source_counts,
                'recommendations': self._generate_recommendations(all_businesses)
            }
            
            # Write report file
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(report, jsonfile, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully generated summary report at {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
            raise
    
    def _get_filtered_businesses(self, filters: Optional[Dict] = None) -> List[Business]:
        """Get businesses with optional filters"""
        query = self.session.query(Business)
        
        if not filters:
            return query.all()
        
        # Apply filters
        if 'human_review' in filters:
            query = query.filter(Business.human_review == filters['human_review'])
        
        if 'confidence_score_min' in filters:
            query = query.filter(Business.confidence_score >= filters['confidence_score_min'])
        
        if 'no_website_no_social' in filters:
            query = query.filter(Business.no_website_no_social == filters['no_website_no_social'])
        
        if 'website_present' in filters:
            query = query.filter(Business.website_present == filters['website_present'])
        
        if 'social_present' in filters:
            query = query.filter(Business.social_present == filters['social_present'])
        
        if 'city' in filters:
            query = query.filter(Business.city.ilike(f"%{filters['city']}%"))
        
        if 'source' in filters:
            query = query.filter(Business.sources.contains([filters['source']]))
        
        return query.all()
    
    def _generate_recommendations(self, businesses: List[Business]) -> List[str]:
        """Generate recommendations based on data analysis"""
        recommendations = []
        
        # Check for data quality issues
        businesses_without_address = len([b for b in businesses if not b.address])
        if businesses_without_address > len(businesses) * 0.1:  # More than 10%
            recommendations.append(f"Consider improving address data quality. {businesses_without_address} businesses lack address information.")
        
        # Check for low confidence predictions
        low_confidence_count = len([b for b in businesses if b.confidence_score and b.confidence_score < 0.5])
        if low_confidence_count > len(businesses) * 0.2:  # More than 20%
            recommendations.append(f"Many predictions have low confidence. Consider improving data sources or model training.")
        
        # Check for pending reviews
        pending_count = len([b for b in businesses if not b.human_review])
        if pending_count > len(businesses) * 0.3:  # More than 30%
            recommendations.append(f"High number of pending reviews ({pending_count}). Consider prioritizing review process.")
        
        # Check for source diversity
        source_counts = {}
        for business in businesses:
            if business.sources:
                for source in business.sources:
                    source_counts[source] = source_counts.get(source, 0) + 1
        
        if len(source_counts) < 2:
            recommendations.append("Consider diversifying data sources to improve accuracy.")
        
        return recommendations
    
    def close(self):
        """Close database session"""
        self.session.close()

# Example usage and testing
if __name__ == "__main__":
    exporter = BusinessExporter()
    
    # Export all businesses
    # exporter.export_to_csv("all_businesses.csv")
    
    # Export approved businesses only
    # exporter.export_approved_only("approved_businesses.csv")
    
    # Export high confidence predictions
    # exporter.export_high_confidence("high_confidence.csv", confidence_threshold=0.8)
    
    # Generate summary report
    # exporter.export_summary_report("summary_report.json")
    
    exporter.close()
