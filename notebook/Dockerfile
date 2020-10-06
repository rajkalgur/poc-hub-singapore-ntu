#FROM myproject/minimal-notebook:latest
FROM jupyter/minimal-notebook:latest

USER root

# Required for ffmpeg.

RUN yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm --skip-broken && \
    yum-config-manager -y --add-repo https://negativo17.org/repos/epel-multimedia.repo --skip-broken && \
    yum install --enablerepo=epel -y ffmpeg --skip-broken && \
    yum -y clean all --enablerepo='*' --skip-broken

RUN yum install -y libaio && \
    rpm -i https://download.oracle.com/otn_software/linux/instantclient/19800/oracle-instantclient19.8-basic-19.8.0.0.0-1.x86_64.rpm && \
    rpm -i https://download.oracle.com/otn_software/linux/instantclient/19800/oracle-instantclient19.8-sqlplus-19.8.0.0.0-1.x86_64.rpm && \
    pip install --upgrade snowflake-connector-python && \
    pip install google-cloud-storage && \
    pip install boto3 && \
    pip install cx_oracle

RUN apt-get update && \
    apt-get install -y --no-install-recommends libav-tools rsync && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*	
	
LABEL io.k8s.description="S2I builder for Jupyter (minimal-notebook)." \
      io.k8s.display-name="Jupyter (minimal-notebook)" \
      io.openshift.expose-services="8888:http" \
      io.openshift.tags="builder,python,jupyter" \
      io.openshift.s2i.scripts-url="image:///opt/app-root/s2i/bin"

COPY s2i /opt/app-root/s2i

USER 1000

CMD [ "/opt/app-root/s2i/bin/run" ]