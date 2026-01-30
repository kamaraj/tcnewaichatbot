import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, ScrollView } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { uploadDocument } from '../api/client';

export default function UploadScreen({ navigation }) {
    const [uploading, setUploading] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    const pickDocument = async () => {
        try {
            const result = await DocumentPicker.getDocumentAsync({
                type: 'application/pdf',
                copyToCacheDirectory: true,
                multiple: true,
            });

            if (result.canceled) return;

            for (const file of result.assets) {
                await handleUpload(file);
            }
        } catch (err) {
            Alert.alert("Error", "Failed to pick document");
        }
    };

    const handleUpload = async (file) => {
        setUploading(true);
        const fileEntry = {
            name: file.name,
            status: 'uploading',
            metrics: null
        };
        setUploadedFiles(prev => [...prev, fileEntry]);

        try {
            const response = await uploadDocument(file);
            setUploadedFiles(prev =>
                prev.map(f => f.name === file.name
                    ? { ...f, status: 'processing', metrics: response }
                    : f
                )
            );
        } catch (error) {
            setUploadedFiles(prev =>
                prev.map(f => f.name === file.name
                    ? { ...f, status: 'failed' }
                    : f
                )
            );
            Alert.alert("Error", "Upload failed. Check backend connection.");
        } finally {
            setUploading(false);
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'uploading': return '⏳';
            case 'processing': return '🔄';
            case 'completed': return '✅';
            case 'failed': return '❌';
            default: return '📄';
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'uploading': return '#f59e0b';
            case 'processing': return '#6366f1';
            case 'completed': return '#10b981';
            case 'failed': return '#ef4444';
            default: return '#94a3b8';
        }
    };

    return (
        <ScrollView style={styles.container}>
            {/* Upload Zone */}
            <TouchableOpacity
                style={styles.uploadZone}
                onPress={pickDocument}
                disabled={uploading}
            >
                {uploading ? (
                    <>
                        <ActivityIndicator size="large" color="#6366f1" />
                        <Text style={styles.uploadText}>Uploading...</Text>
                    </>
                ) : (
                    <>
                        <Text style={styles.uploadIcon}>📁</Text>
                        <Text style={styles.uploadTitle}>Tap to Select PDFs</Text>
                        <Text style={styles.uploadSubtitle}>Only PDF files are supported</Text>
                    </>
                )}
            </TouchableOpacity>

            {/* Uploaded Files */}
            {uploadedFiles.length > 0 && (
                <View style={styles.filesSection}>
                    <Text style={styles.sectionTitle}>Uploaded Files</Text>
                    {uploadedFiles.map((file, index) => (
                        <View key={index} style={styles.fileCard}>
                            <Text style={styles.fileIcon}>{getStatusIcon(file.status)}</Text>
                            <View style={styles.fileInfo}>
                                <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
                                <Text style={[styles.fileStatus, { color: getStatusColor(file.status) }]}>
                                    {file.status === 'processing' ? 'Processing in background...' : file.status}
                                </Text>
                            </View>
                            {file.metrics && (
                                <Text style={styles.fileMetric}>
                                    {file.metrics.upload_time_ms}ms
                                </Text>
                            )}
                        </View>
                    ))}
                </View>
            )}

            {/* Instructions */}
            <View style={styles.infoCard}>
                <Text style={styles.infoTitle}>📋 How it works</Text>
                <View style={styles.infoStep}>
                    <Text style={styles.stepNumber}>1</Text>
                    <Text style={styles.stepText}>Upload your PDF documents</Text>
                </View>
                <View style={styles.infoStep}>
                    <Text style={styles.stepNumber}>2</Text>
                    <Text style={styles.stepText}>Documents are chunked & embedded</Text>
                </View>
                <View style={styles.infoStep}>
                    <Text style={styles.stepNumber}>3</Text>
                    <Text style={styles.stepText}>Ask questions in the Chat</Text>
                </View>
                <View style={styles.infoStep}>
                    <Text style={styles.stepNumber}>4</Text>
                    <Text style={styles.stepText}>Get answers grounded in your docs</Text>
                </View>
            </View>

            {/* Action Button */}
            {uploadedFiles.length > 0 && (
                <TouchableOpacity
                    style={styles.chatButton}
                    onPress={() => navigation.navigate('Chat')}
                >
                    <Text style={styles.chatButtonText}>💬 Start Chatting</Text>
                </TouchableOpacity>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0f172a',
        padding: 20,
    },
    uploadZone: {
        backgroundColor: '#1e293b',
        borderRadius: 16,
        borderWidth: 2,
        borderColor: '#334155',
        borderStyle: 'dashed',
        padding: 40,
        alignItems: 'center',
        justifyContent: 'center',
    },
    uploadIcon: {
        fontSize: 48,
        marginBottom: 16,
    },
    uploadTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#f1f5f9',
        marginBottom: 8,
    },
    uploadSubtitle: {
        fontSize: 14,
        color: '#94a3b8',
    },
    uploadText: {
        fontSize: 16,
        color: '#6366f1',
        marginTop: 12,
    },
    filesSection: {
        marginTop: 24,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#f1f5f9',
        marginBottom: 12,
    },
    fileCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#1e293b',
        borderRadius: 12,
        padding: 16,
        marginBottom: 8,
        borderWidth: 1,
        borderColor: '#334155',
    },
    fileIcon: {
        fontSize: 24,
        marginRight: 12,
    },
    fileInfo: {
        flex: 1,
    },
    fileName: {
        color: '#f1f5f9',
        fontSize: 14,
        fontWeight: '500',
    },
    fileStatus: {
        fontSize: 12,
        marginTop: 2,
        textTransform: 'capitalize',
    },
    fileMetric: {
        color: '#6366f1',
        fontSize: 12,
        fontWeight: '600',
    },
    infoCard: {
        backgroundColor: '#1e293b',
        borderRadius: 12,
        padding: 20,
        marginTop: 24,
        borderWidth: 1,
        borderColor: '#334155',
    },
    infoTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#f1f5f9',
        marginBottom: 16,
    },
    infoStep: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    stepNumber: {
        width: 24,
        height: 24,
        borderRadius: 12,
        backgroundColor: '#6366f1',
        color: 'white',
        textAlign: 'center',
        lineHeight: 24,
        fontSize: 12,
        fontWeight: '700',
        marginRight: 12,
    },
    stepText: {
        color: '#94a3b8',
        fontSize: 14,
    },
    chatButton: {
        backgroundColor: '#6366f1',
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
        marginTop: 24,
        marginBottom: 40,
    },
    chatButtonText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
    },
});
