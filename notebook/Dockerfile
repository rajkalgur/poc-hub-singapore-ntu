FROM myproject/minimal-notebook:latest

USER root

# Required for ffmpeg.

#RUN yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm --skip-broken && \
#    yum-config-manager -y --add-repo https://negativo17.org/repos/epel-multimedia.repo --skip-broken && \
#    yum install --enablerepo=epel -y ffmpeg --skip-broken && \
#    yum -y clean all --enablerepo='*' --skip-broken

#RUN yum install -y libaio
#RUN rpm -i https://download.oracle.com/otn_software/linux/instantclient/19800/oracle-instantclient19.8-basic-19.8.0.0.0-1.x86_64.rpm
#RUN rpm -i https://download.oracle.com/otn_software/linux/instantclient/19800/oracle-instantclient19.8-sqlplus-19.8.0.0.0-1.x86_64.rpm 

RUN pip install --upgrade snowflake-connector-python

RUN pip install -google-cloud-storage
RUN pip install boto3
RUN pip install cx_oracle 


USER 1001
